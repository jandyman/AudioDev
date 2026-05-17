// swift-tools-version: 5.9
import PackageDescription

let package = Package(
  name: "DaisyControl",
  platforms: [.macOS(.v14)],
  targets: [
    .executableTarget(
      name: "DaisyControl",
      path: "Sources/DaisyControl"
    )
  ]
)
