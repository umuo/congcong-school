import SwiftUI

@main
@MainActor
struct ChinaTextbookStudyApp: App {
    var body: some Scene {
        WindowGroup {
            CloudRootView()
                .tint(Color(red: 0.08, green: 0.48, blue: 0.30))
        }
    }
}
