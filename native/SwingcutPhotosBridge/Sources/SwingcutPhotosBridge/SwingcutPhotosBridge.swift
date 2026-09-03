import Foundation
import Photos

struct BridgeInfo {
  static let version = "0.2.0"
}

struct BridgeError: Error, CustomStringConvertible {
  let description: String
}

struct AssetRecord: Codable {
  let assetID: String
  let filename: String
  let creationDate: String?
  let durationSeconds: Double
  let width: Int
  let height: Int
}

struct ListResult: Codable {
  let album: String
  let assets: [AssetRecord]
}

struct ExportResult: Codable {
  let assetID: String
  let outputPath: String
  let bytes: UInt64
}

struct ImportResult: Codable {
  let assetID: String
  let verified: Bool
}

struct Capabilities: Encodable {
  let readOperations = ["status", "albums", "library-counts", "list", "export"]
  let writeOperations = ["import-output"]
}

struct TransportArguments {
  let command: [String]
  let resultPath: String?
  let errorPath: String?
  let cancelPath: String?
}

final class SendableBox<Value>: @unchecked Sendable {
  private let lock = NSLock()
  private var value: Value?

  func set(_ newValue: Value) {
    lock.lock()
    value = newValue
    lock.unlock()
  }

  func get() -> Value? {
    lock.lock()
    defer { lock.unlock() }
    return value
  }
}

@main
struct SwingcutPhotosBridge {
  static func main() {
    let rawArguments = Array(CommandLine.arguments.dropFirst())
    var errorPath: String?
    do {
      let transport = try parseTransport(rawArguments)
      errorPath = transport.errorPath
      try run(transport)
    } catch {
      writeError(
        error, outputPath: errorPath ?? optionalValue(after: "--error-file", in: rawArguments))
      Foundation.exit(EXIT_FAILURE)
    }
  }

  static func run(_ transport: TransportArguments) throws {
    let arguments = transport.command
    try checkCancellation(transport.cancelPath)
    if arguments == ["--version"] {
      try writeOutput(
        "swingcut-photos-bridge \(BridgeInfo.version)\n", outputPath: transport.resultPath)
      return
    }
    if arguments == ["capabilities"] {
      try writeJSON(Capabilities(), outputPath: transport.resultPath)
      return
    }

    guard let command = arguments.first else {
      throw BridgeError(description: usage)
    }

    switch command {
    case "status":
      try requireExactArguments(arguments, count: 1)
      try writeOutput(
        "\(authorizationLabel(PHPhotoLibrary.authorizationStatus(for: .readWrite)))\n",
        outputPath: transport.resultPath
      )
    case "albums":
      try requireExactArguments(arguments, count: 1)
      try requireReadAccess()
      try checkCancellation(transport.cancelPath)
      try writeJSON(listAlbumTitles(), outputPath: transport.resultPath)
    case "library-counts":
      try requireExactArguments(arguments, count: 1)
      try requireReadAccess()
      try checkCancellation(transport.cancelPath)
      try writeJSON(libraryCounts(), outputPath: transport.resultPath)
    case "list":
      try requireExactArguments(arguments, count: 3)
      let album = try value(after: "--album", in: arguments)
      try requireReadAccess()
      try checkCancellation(transport.cancelPath)
      try writeJSON(try listVideos(albumTitle: album), outputPath: transport.resultPath)
    case "export":
      try requireExactArguments(arguments, count: 5)
      let assetID = try value(after: "--asset-id", in: arguments)
      let output = try value(after: "--output", in: arguments)
      try requireReadAccess()
      try writeJSON(
        try exportOriginal(assetID: assetID, outputPath: output, cancelPath: transport.cancelPath),
        outputPath: transport.resultPath
      )
    case "import-output":
      try requireExactArguments(arguments, count: 3)
      let input = try value(after: "--input", in: arguments)
      try requireReadAccess()
      try checkCancellation(transport.cancelPath)
      try writeJSON(try importOutput(inputPath: input), outputPath: transport.resultPath)
    default:
      throw BridgeError(description: "Unknown command: \(command)\n\(usage)")
    }
  }

  static let usage = """
    Usage:
      swingcut-photos-bridge --version
      swingcut-photos-bridge capabilities
      swingcut-photos-bridge status
      swingcut-photos-bridge albums
      swingcut-photos-bridge library-counts
      swingcut-photos-bridge list --album ALBUM
      swingcut-photos-bridge export --asset-id ID --output PATH
      swingcut-photos-bridge import-output --input PATH

    App-bundle invocations may add --result-file, --error-file, and --cancel-file paths.
    """

  static func parseTransport(_ arguments: [String]) throws -> TransportArguments {
    let transportFlags = Set(["--result-file", "--error-file", "--cancel-file"])
    var command: [String] = []
    var values: [String: String] = [:]
    var index = 0
    while index < arguments.count {
      let argument = arguments[index]
      if transportFlags.contains(argument) {
        guard values[argument] == nil, arguments.indices.contains(index + 1) else {
          throw BridgeError(description: "Invalid or repeated transport argument \(argument)")
        }
        values[argument] = arguments[index + 1]
        index += 2
      } else {
        command.append(argument)
        index += 1
      }
    }
    return TransportArguments(
      command: command,
      resultPath: values["--result-file"],
      errorPath: values["--error-file"],
      cancelPath: values["--cancel-file"]
    )
  }

  static func optionalValue(after flag: String, in arguments: [String]) -> String? {
    guard let index = arguments.firstIndex(of: flag), arguments.indices.contains(index + 1) else {
      return nil
    }
    return arguments[index + 1]
  }

  static func value(after flag: String, in arguments: [String]) throws -> String {
    guard let index = arguments.firstIndex(of: flag), arguments.indices.contains(index + 1) else {
      throw BridgeError(description: "Missing required argument \(flag)")
    }
    return arguments[index + 1]
  }

  static func requireExactArguments(_ arguments: [String], count: Int) throws {
    guard arguments.count == count else {
      throw BridgeError(description: "Unexpected arguments\n\(usage)")
    }
  }

  static func checkCancellation(_ path: String?) throws {
    if let path, FileManager.default.fileExists(atPath: path) {
      throw BridgeError(description: "Operation cancelled")
    }
  }

  static func requireReadAccess() throws {
    var status = PHPhotoLibrary.authorizationStatus(for: .readWrite)
    if status == .notDetermined {
      let semaphore = DispatchSemaphore(value: 0)
      let statusBox = SendableBox<PHAuthorizationStatus>()
      PHPhotoLibrary.requestAuthorization(for: .readWrite) { newStatus in
        statusBox.set(newStatus)
        semaphore.signal()
      }
      semaphore.wait()
      guard let requestedStatus = statusBox.get() else {
        throw BridgeError(description: "Photos authorization returned no status")
      }
      status = requestedStatus
    }

    guard status == .authorized || status == .limited else {
      throw BridgeError(
        description:
          "Photos read/write access is \(authorizationLabel(status)). Grant access in System Settings > Privacy & Security > Photos."
      )
    }
  }

  static func authorizationLabel(_ status: PHAuthorizationStatus) -> String {
    switch status {
    case .notDetermined: "not-determined"
    case .restricted: "restricted"
    case .denied: "denied"
    case .authorized: "authorized"
    case .limited: "limited"
    @unknown default: "unknown"
    }
  }

  static func libraryCounts() -> [String: Int] {
    let allAssets = PHAsset.fetchAssets(with: nil)
    let videoOptions = PHFetchOptions()
    videoOptions.predicate = NSPredicate(
      format: "mediaType == %d",
      PHAssetMediaType.video.rawValue
    )
    let videos = PHAsset.fetchAssets(with: videoOptions)
    return ["assets": allAssets.count, "videos": videos.count, "albums": userAlbums().count]
  }

  static func userAlbums() -> [PHAssetCollection] {
    let topLevel = PHCollectionList.fetchTopLevelUserCollections(with: nil)
    var albums: [PHAssetCollection] = []
    var visitedFolders: Set<String> = []

    func collect(_ collections: PHFetchResult<PHCollection>) {
      collections.enumerateObjects { collection, _, _ in
        if let album = collection as? PHAssetCollection {
          albums.append(album)
        } else if let folder = collection as? PHCollectionList,
          visitedFolders.insert(folder.localIdentifier).inserted
        {
          collect(PHCollectionList.fetchCollections(in: folder, options: nil))
        }
      }
    }

    collect(topLevel)
    return albums
  }

  static func listAlbumTitles() -> [String] {
    userAlbums().compactMap(\.localizedTitle).sorted {
      $0.localizedCaseInsensitiveCompare($1) == .orderedAscending
    }
  }

  static func listVideos(albumTitle: String) throws -> ListResult {
    let matches = userAlbums().filter { $0.localizedTitle == albumTitle }

    guard matches.count == 1, let album = matches.first else {
      if matches.isEmpty {
        throw BridgeError(description: "No Photos album named exactly '\(albumTitle)' was found")
      }
      throw BridgeError(
        description:
          "More than one Photos album is named '\(albumTitle)'; make the album name unique"
      )
    }

    let options = PHFetchOptions()
    options.predicate = NSPredicate(format: "mediaType == %d", PHAssetMediaType.video.rawValue)
    options.sortDescriptors = [NSSortDescriptor(key: "creationDate", ascending: true)]
    let assets = PHAsset.fetchAssets(in: album, options: options)
    let formatter = ISO8601DateFormatter()
    var records: [AssetRecord] = []
    assets.enumerateObjects { asset, _, _ in
      let resources = PHAssetResource.assetResources(for: asset)
      let filename =
        resources.first(where: { $0.type == .fullSizeVideo })?.originalFilename
        ?? resources.first(where: { $0.type == .video })?.originalFilename
        ?? "unknown-video"
      records.append(
        AssetRecord(
          assetID: asset.localIdentifier,
          filename: filename,
          creationDate: asset.creationDate.map(formatter.string(from:)),
          durationSeconds: asset.duration,
          width: asset.pixelWidth,
          height: asset.pixelHeight
        )
      )
    }
    return ListResult(album: albumTitle, assets: records)
  }

  static func exportOriginal(
    assetID: String,
    outputPath: String,
    cancelPath: String?
  ) throws -> ExportResult {
    let fetched = PHAsset.fetchAssets(withLocalIdentifiers: [assetID], options: nil)
    guard let asset = fetched.firstObject, asset.mediaType == .video else {
      throw BridgeError(description: "The requested video asset was not found")
    }

    let resources = PHAssetResource.assetResources(for: asset)
    guard
      let resource =
        resources.first(where: { $0.type == .fullSizeVideo })
        ?? resources.first(where: { $0.type == .video })
    else {
      throw BridgeError(description: "The requested asset has no exportable video resource")
    }

    let outputURL = URL(fileURLWithPath: outputPath).standardizedFileURL
    guard !FileManager.default.fileExists(atPath: outputURL.path) else {
      throw BridgeError(description: "Refusing to overwrite existing output: \(outputURL.path)")
    }
    try FileManager.default.createDirectory(
      at: outputURL.deletingLastPathComponent(),
      withIntermediateDirectories: true,
      attributes: [.posixPermissions: 0o700]
    )
    guard
      FileManager.default.createFile(
        atPath: outputURL.path,
        contents: nil,
        attributes: [.posixPermissions: 0o600]
      )
    else {
      throw BridgeError(description: "Could not create private export output")
    }

    let handle = try FileHandle(forWritingTo: outputURL)
    let options = PHAssetResourceRequestOptions()
    options.isNetworkAccessAllowed = true
    options.progressHandler = { progress in
      let percent = Int(progress * 100)
      FileHandle.standardError.write(Data("download-progress=\(percent)\n".utf8))
    }

    let semaphore = DispatchSemaphore(value: 0)
    let errorBox = SendableBox<Error>()
    let requestID = PHAssetResourceManager.default().requestData(
      for: resource,
      options: options,
      dataReceivedHandler: { data in
        do {
          try handle.write(contentsOf: data)
        } catch {
          errorBox.set(error)
        }
      },
      completionHandler: { error in
        if let error {
          errorBox.set(error)
        }
        semaphore.signal()
      }
    )

    var cancelled = false
    while semaphore.wait(timeout: .now() + 0.1) == .timedOut {
      if let cancelPath, FileManager.default.fileExists(atPath: cancelPath) {
        cancelled = true
        PHAssetResourceManager.default().cancelDataRequest(requestID)
      }
    }
    try? handle.close()

    if cancelled {
      try? FileManager.default.removeItem(at: outputURL)
      throw BridgeError(description: "Operation cancelled")
    }
    if let exportError = errorBox.get() {
      try? FileManager.default.removeItem(at: outputURL)
      throw exportError
    }
    let attributes = try FileManager.default.attributesOfItem(atPath: outputURL.path)
    let bytes = (attributes[.size] as? NSNumber)?.uint64Value ?? 0
    guard bytes > 0 else {
      try? FileManager.default.removeItem(at: outputURL)
      throw BridgeError(description: "Photos export completed but produced an empty file")
    }
    return ExportResult(assetID: assetID, outputPath: outputURL.path, bytes: bytes)
  }

  static func importOutput(inputPath: String) throws -> ImportResult {
    let inputURL = URL(fileURLWithPath: inputPath).standardizedFileURL
    let values = try inputURL.resourceValues(forKeys: [
      .isRegularFileKey, .isSymbolicLinkKey, .fileSizeKey,
    ])
    guard values.isRegularFile == true, values.isSymbolicLink != true, (values.fileSize ?? 0) > 0
    else {
      throw BridgeError(description: "Import requires a non-empty regular local video file")
    }

    let identifierBox = SendableBox<String>()
    try PHPhotoLibrary.shared().performChangesAndWait {
      guard
        let request = PHAssetChangeRequest.creationRequestForAssetFromVideo(atFileURL: inputURL),
        let identifier = request.placeholderForCreatedAsset?.localIdentifier
      else {
        return
      }
      identifierBox.set(identifier)
    }
    guard let identifier = identifierBox.get() else {
      throw BridgeError(description: "Photos did not create an output asset placeholder")
    }
    let fetched = PHAsset.fetchAssets(withLocalIdentifiers: [identifier], options: nil)
    guard let created = fetched.firstObject, created.mediaType == .video else {
      throw BridgeError(description: "Photos creation could not be verified after import")
    }
    return ImportResult(assetID: identifier, verified: true)
  }

  static func writeJSON<Value: Encodable>(_ value: Value, outputPath: String?) throws {
    let encoder = JSONEncoder()
    encoder.outputFormatting = [.sortedKeys]
    let data = try encoder.encode(value)
    guard let text = String(data: data, encoding: .utf8) else {
      throw BridgeError(description: "Could not encode JSON output")
    }
    try writeOutput("\(text)\n", outputPath: outputPath)
  }

  static func writeOutput(_ text: String, outputPath: String?) throws {
    guard let outputPath else {
      print(text, terminator: "")
      return
    }
    let url = URL(fileURLWithPath: outputPath).standardizedFileURL
    try FileManager.default.createDirectory(
      at: url.deletingLastPathComponent(),
      withIntermediateDirectories: true,
      attributes: [.posixPermissions: 0o700]
    )
    try Data(text.utf8).write(to: url, options: .atomic)
    try FileManager.default.setAttributes([.posixPermissions: 0o600], ofItemAtPath: url.path)
  }

  static func writeError(_ error: Error, outputPath: String?) {
    let message = "swingcut-photos-bridge: \(error)\n"
    if let outputPath {
      try? writeOutput(message, outputPath: outputPath)
    } else {
      FileHandle.standardError.write(Data(message.utf8))
    }
  }
}
