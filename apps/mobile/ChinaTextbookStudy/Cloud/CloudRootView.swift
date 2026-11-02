import SwiftUI
import UIKit
import WebKit

@MainActor
struct CloudRootView: View {
    @StateObject private var browser = CloudBrowser()
    @Environment(\.scenePhase) private var scenePhase

    var body: some View {
        VStack(spacing: 0) {
            HStack(spacing: 16) {
                Button(action: { browser.webView.goBack() }) {
                    Image(systemName: "chevron.backward")
                }
                .accessibilityLabel("后退")
                .disabled(!browser.canGoBack)
                VStack(alignment: .leading, spacing: 2) {
                    Text("聪聪学堂 · 云端测试").font(.headline)
                    Text("study.lacknb.com").font(.caption).foregroundStyle(.secondary)
                }
                Spacer()
                Button(action: browser.reload) { Image(systemName: "arrow.clockwise") }
                    .accessibilityLabel("重新连接")
            }
            .padding(.horizontal).frame(minHeight: 52)
            if browser.loading { ProgressView().progressViewStyle(.linear) }
            ZStack {
                CloudWebView(webView: browser.webView)
                if let failure = browser.failure {
                    VStack(spacing: 16) {
                        Image(systemName: "wifi.exclamationmark").font(.largeTitle)
                        Text("暂时无法连接学堂").font(.headline)
                        Text(failure).multilineTextAlignment(.center)
                        Button("重新连接", action: browser.reload).buttonStyle(.borderedProminent)
                    }
                    .padding(28).frame(maxWidth: .infinity, maxHeight: .infinity)
                    .background(.background)
                }
            }
        }
        .background(Color(.systemBackground))
        .overlay {
            if scenePhase != .active {
                VStack(spacing: 12) {
                    Image(systemName: "leaf.fill").font(.largeTitle)
                    Text("聪聪学堂").font(.title2.bold())
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity).background(.background)
            }
        }
        .sheet(item: $browser.sharedFile, onDismiss: browser.removeSharedFile) { file in
            CloudShareSheet(file: file.url)
        }
    }
}

private struct CloudWebView: UIViewRepresentable {
    let webView: WKWebView
    func makeUIView(context: Context) -> WKWebView { webView }
    func updateUIView(_ view: WKWebView, context: Context) {}
}

private struct CloudShareSheet: UIViewControllerRepresentable {
    let file: URL
    func makeUIViewController(context: Context) -> UIActivityViewController {
        UIActivityViewController(activityItems: [file], applicationActivities: nil)
    }
    func updateUIViewController(_ view: UIActivityViewController, context: Context) {}
}
