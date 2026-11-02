import SwiftUI
import UIKit
import WebKit

@MainActor
final class CloudBrowser: NSObject, ObservableObject, WKNavigationDelegate, WKUIDelegate, WKDownloadDelegate {
    struct SharedFile: Identifiable {
        let id = UUID()
        let url: URL
    }
    let webView: WKWebView
    @Published var loading = true
    @Published var canGoBack = false
    @Published var failure: String?
    @Published var sharedFile: SharedFile?
    private var observations: [NSKeyValueObservation] = []
    private var downloadFiles: [ObjectIdentifier: URL] = [:]
    private var sharedDirectory: URL?

    override init() {
        let configuration = WKWebViewConfiguration()
        configuration.websiteDataStore = .default()
        configuration.allowsInlineMediaPlayback = true
        configuration.mediaTypesRequiringUserActionForPlayback = []
        webView = WKWebView(frame: .zero, configuration: configuration)
        super.init()
        webView.navigationDelegate = self
        webView.uiDelegate = self
        webView.allowsBackForwardNavigationGestures = true
        observations = [
            webView.observe(\.isLoading, options: [.initial, .new]) { [weak self] view, _ in
                self?.loading = view.isLoading
            },
            webView.observe(\.canGoBack, options: [.initial, .new]) { [weak self] view, _ in
                self?.canGoBack = view.canGoBack
            }
        ]
        webView.load(URLRequest(url: CloudOrigin.home, timeoutInterval: 30))
    }

    func reload() {
        failure = nil
        if webView.url != nil { webView.reload() }
        else { webView.load(URLRequest(url: CloudOrigin.home, timeoutInterval: 30)) }
    }

    func webView(_ webView: WKWebView, decidePolicyFor action: WKNavigationAction,
                 decisionHandler: @escaping (WKNavigationActionPolicy) -> Void) {
        guard let url = action.request.url else { decisionHandler(.cancel); return }
        // Blob URLs are used by the authenticated export and local report downloads.
        if url.scheme == "blob", url.absoluteString.hasPrefix("blob:https://study.lacknb.com:8443/") {
            decisionHandler(action.shouldPerformDownload ? .download : .allow)
            return
        }
        guard CloudOrigin.allows(url) else {
            decisionHandler(.cancel)
            if action.navigationType == .linkActivated, url.scheme == "https" {
                UIApplication.shared.open(url)
            }
            return
        }
        if action.shouldPerformDownload { decisionHandler(.download) }
        else if action.targetFrame == nil {
            decisionHandler(.cancel)
            webView.load(action.request)
        } else { decisionHandler(.allow) }
    }

    func webView(_ webView: WKWebView, decidePolicyFor response: WKNavigationResponse,
                 decisionHandler: @escaping (WKNavigationResponsePolicy) -> Void) {
        decisionHandler(response.canShowMIMEType ? .allow : .download)
    }

    func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) { failure = nil }
    func webView(_ webView: WKWebView, didFailProvisionalNavigation navigation: WKNavigation!, withError error: Error) {
        navigationFailed(error)
    }
    func webView(_ webView: WKWebView, didFail navigation: WKNavigation!, withError error: Error) {
        navigationFailed(error)
    }
    func webViewWebContentProcessDidTerminate(_ webView: WKWebView) {
        failure = "页面已暂停。请重新连接；已确认的学习记录保存在云端。"
    }
    private func navigationFailed(_ error: Error) {
        if (error as NSError).code == NSURLErrorCancelled { return }
        failure = "请检查网络后重试。尚未确认的操作需要返回原账号同步。"
        loading = false
    }

    func webView(_ webView: WKWebView, requestMediaCapturePermissionFor origin: WKSecurityOrigin,
                 initiatedByFrame frame: WKFrameInfo, type: WKMediaCaptureType,
                 decisionHandler: @escaping (WKPermissionDecision) -> Void) {
        let allowed = type == .microphone
            && CloudOrigin.allowsMedia(protocol: origin.protocol, host: origin.host, port: origin.port)
            && CloudOrigin.allowsMedia(protocol: frame.securityOrigin.protocol,
                                       host: frame.securityOrigin.host, port: frame.securityOrigin.port)
        decisionHandler(allowed ? .prompt : .deny)
    }

    func webView(_ webView: WKWebView, runJavaScriptAlertPanelWithMessage message: String,
                 initiatedByFrame frame: WKFrameInfo, completionHandler: @escaping () -> Void) {
        guard let presenter = presenter() else { completionHandler(); return }
        let alert = UIAlertController(title: "学堂提示", message: String(message.prefix(2000)), preferredStyle: .alert)
        alert.addAction(UIAlertAction(title: "确定", style: .default) { _ in completionHandler() })
        presenter.present(alert, animated: true)
    }
    func webView(_ webView: WKWebView, runJavaScriptConfirmPanelWithMessage message: String,
                 initiatedByFrame frame: WKFrameInfo, completionHandler: @escaping (Bool) -> Void) {
        guard let presenter = presenter() else { completionHandler(false); return }
        let alert = UIAlertController(title: "请确认", message: String(message.prefix(2000)), preferredStyle: .alert)
        alert.addAction(UIAlertAction(title: "取消", style: .cancel) { _ in completionHandler(false) })
        alert.addAction(UIAlertAction(title: "确定", style: .default) { _ in completionHandler(true) })
        presenter.present(alert, animated: true)
    }
    private func presenter() -> UIViewController? {
        var controller = webView.window?.rootViewController
        while let presented = controller?.presentedViewController { controller = presented }
        return controller
    }

    func webView(_ webView: WKWebView, navigationAction: WKNavigationAction, didBecome download: WKDownload) {
        download.delegate = self
    }
    func webView(_ webView: WKWebView, navigationResponse: WKNavigationResponse, didBecome download: WKDownload) {
        download.delegate = self
    }
    func download(_ download: WKDownload, decideDestinationUsing response: URLResponse,
                  suggestedFilename: String, completionHandler: @escaping (URL?) -> Void) {
        do {
            let directory = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString, isDirectory: true)
            try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
            let file = directory.appendingPathComponent(CloudOrigin.downloadName(suggestedFilename))
            downloadFiles[ObjectIdentifier(download)] = file
            completionHandler(file)
        } catch { completionHandler(nil) }
    }
    func downloadDidFinish(_ download: WKDownload) {
        guard let url = downloadFiles.removeValue(forKey: ObjectIdentifier(download)) else { return }
        removeSharedFile()
        sharedDirectory = url.deletingLastPathComponent()
        sharedFile = SharedFile(url: url)
    }
    func download(_ download: WKDownload, didFailWithError error: Error, resumeData: Data?) {
        if let file = downloadFiles.removeValue(forKey: ObjectIdentifier(download)) {
            try? FileManager.default.removeItem(at: file.deletingLastPathComponent())
        }
        guard let presenter = presenter() else { return }
        let alert = UIAlertController(title: "下载未完成", message: "请保持当前账号，返回页面重新下载。", preferredStyle: .alert)
        alert.addAction(UIAlertAction(title: "确定", style: .default))
        presenter.present(alert, animated: true)
    }
    func removeSharedFile() {
        if let directory = sharedDirectory { try? FileManager.default.removeItem(at: directory) }
        sharedDirectory = nil
    }
}
