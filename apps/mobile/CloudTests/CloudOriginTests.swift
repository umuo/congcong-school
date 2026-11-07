import XCTest
@testable import ChinaTextbookStudy

final class CloudOriginTests: XCTestCase {
    func testOnlyTheConfiguredTLSOriginCanHostLearning() {
        XCTAssertTrue(CloudOrigin.allows(CloudOrigin.home))
        XCTAssertTrue(CloudOrigin.allows(URL(string: "https://study.lacknb.com:8443/learn/?session=test")!))
        for address in ["http://study.lacknb.com:8443/", "https://study.lacknb.com/", "https://study.lacknb.com.evil.test:8443/", "https://evil.test:8443/", "https://user:secret@study.lacknb.com:8443/", "file:///tmp/a.html", "javascript:alert(1)"] {
            XCTAssertFalse(CloudOrigin.allows(URL(string: address)!), address)
        }
    }
    func testMediaRequiresTheExactOrigin() {
        XCTAssertTrue(CloudOrigin.allowsMedia(protocol: "https", host: "study.lacknb.com", port: 8443))
        XCTAssertFalse(CloudOrigin.allowsMedia(protocol: "https", host: "evil.test", port: 8443))
        XCTAssertFalse(CloudOrigin.allowsMedia(protocol: "http", host: "study.lacknb.com", port: 8443))
        XCTAssertFalse(CloudOrigin.allowsMedia(protocol: "https", host: "study.lacknb.com", port: 443))
    }
    func testDownloadNamesCannotEscapeTheTemporaryDirectory() {
        XCTAssertEqual(CloudOrigin.downloadName("../../backup.json"), "backup.json")
        XCTAssertEqual(CloudOrigin.downloadName(""), "congcong-backup.json")
        XCTAssertEqual(CloudOrigin.downloadName(".."), "congcong-backup.json")
    }
}
