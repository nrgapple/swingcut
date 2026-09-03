import Foundation
import Photos

struct BridgeInfo {
  static let version = "0.1.0"
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
    let arguments = Array(CommandLine.arguments.dropFirst())
    do {
      try run(arguments: arguments)
    } catch {
      writeError(error, outputPath: optionalValue(after: "--error-file", in: arguments))
      Foundation.exit(EXIT_FAILURE)
    }
  }

  static func run(arguments: [String]) throws {
    let resultPath = optionalValue(after: "--result-file", in: arguments)
    if arguments == ["--version"] {
      try writeOutput("swingcut-photos-bridge \(BridgeInfo.version)\n", outputPath: resultPath)
      return
    }

    guard let command = arguments.first else {
      throw BridgeError(description: usage)
    }

    switch command {
    case "status":
      try writeOutput(
        "\(authorizationLabel(PHPhotoLibrary.authorizationStatus(for: .readWrite)))\n",
        outputPath: resultPath
      )
    case "albums":
      try requireReadAccess()
      try writeJSON(listAlbumTitles(), outputPath: resultPath)
    case "library-counts":
      try requireReadAccess()
      try writeJSON(libraryCounts(), outputPath: resultPath)
    case "list":
      let album = try value(after: "--album", in: arguments)
      try requireReadAccess()
      try writeJSON(listVideos(albumTitle: album), outputPath: resultPath)
    case "export":
      let assetID = try value(after: "--asset-id", in: arguments)
      let output = try value(after: "--output", in: arguments)
      try requireReadAccess()
      try writeJSON(exportOriginal(assetID: assetID, outputPath: output), outputPath: resultPath)
    default:
      throw BridgeError(description: "Unknown command: \(command)\n\(usage)")
    }
  }

  static let usage = """
    Usage:
      swingcut-photos-bridge --version
      swingcut-photos-bridge status
      swingcut-photos-bridge albums
      swingcut-photos-bridge library-counts
      swingcut-photos-bridge list --album ALBUM
      swingcut-photos-bridge export --asset-id ID --output PATH

    App-bundle invocations may add --result-file PATH and --error-file PATH.
    """

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
          "Photos read access is \(authorizationLabel(status)). Grant access in System Settings > Privacy & Security > Photos."
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

  static func exportOriginal(assetID: String, outputPath: String) throws -> ExportResult {
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
      withIntermediateDirectories: true
    )

    let options = PHAssetResourceRequestOptions()
    options.isNetworkAccessAllowed = true
    options.progressHandler = { progress in
      let percent = Int(progress * 100)
      FileHandle.standardError.write(Data("download-progress=\(percent)\n".utf8))
    }

    let semaphore = DispatchSemaphore(value: 0)
    let errorBox = SendableBox<Error>()
    PHAssetResourceManager.default().writeData(
      for: resource,
      toFile: outputURL,
      options: options
    ) { error in
      if let error {
        errorBox.set(error)
      }
      semaphore.signal()
    }
    semaphore.wait()

    if let exportError = errorBox.get() {
      throw exportError
    }
    let attributes = try FileManager.default.attributesOfItem(atPath: outputURL.path)
    let bytes = (attributes[.size] as? NSNumber)?.uint64Value ?? 0
    guard bytes > 0 else {
      throw BridgeError(description: "Photos export completed but produced an empty file")
    }
    return ExportResult(assetID: assetID, outputPath: outputURL.path, bytes: bytes)
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
      withIntermediateDirectories: true
    )
    try Data(text.utf8).write(to: url, options: .atomic)
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
