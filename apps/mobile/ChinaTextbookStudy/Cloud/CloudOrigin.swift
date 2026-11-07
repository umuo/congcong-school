import Foundation

/// The cloud app never falls back to the bundled, answer-bearing offline library.
enum CloudOrigin {
    static let home = URL(string: "https://study.lacknb.com:8443/login/")!

    static func allows(_ url: URL) -> Bool {
        url.scheme?.lowercased() == "https"
            && url.host?.lowercased() == home.host
            && (url.port ?? 443) == home.port
            && url.user == nil && url.password == nil
    }

    static func allowsMedia(protocol scheme: String, host: String, port: Int) -> Bool {
        scheme.lowercased() == "https" && host.lowercased() == home.host && port == home.port
    }

    static func downloadName(_ suggested: String) -> String {
        let name = (suggested as NSString).lastPathComponent
        return name.isEmpty || name == "." || name == ".." ? "congcong-backup.json" : name
    }
}
