// swift-tools-version: 6.0

import Foundation
import PackageDescription

let packageRoot = URL(fileURLWithPath: #filePath).deletingLastPathComponent().path
let infoPlist = "\(packageRoot)/Info.plist"

let package = Package(
  name: "SwingcutPhotosBridge",
  platforms: [.macOS(.v14)],
  products: [
    .executable(name: "swingcut-photos-bridge", targets: ["SwingcutPhotosBridge"])
  ],
  targets: [
    .executableTarget(
      name: "SwingcutPhotosBridge",
      linkerSettings: [
        .unsafeFlags([
          "-Xlinker", "-sectcreate",
          "-Xlinker", "__TEXT",
          "-Xlinker", "__info_plist",
          "-Xlinker", infoPlist,
        ])
      ]
    )
  ]
)
