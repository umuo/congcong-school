#!/usr/bin/env bash
# Build the existing iOS target as an unsigned, device-arm64 cloud test IPA.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="${IOS_CLOUD_OUT:-$ROOT/deploy-output/ios-cloud}"
DERIVED="${IOS_CLOUD_DERIVED:-$OUT/DerivedData}"
ARCHIVE="$OUT/ChinaTextbookStudy.xcarchive"
if ! xcodebuild -version >/dev/null 2>&1; then
  echo '需要完整 Xcode；Command Line Tools 无法构建 iOS IPA。' >&2
  exit 1
fi
command -v xcodegen >/dev/null || { echo '请安装 XcodeGen：brew install xcodegen' >&2; exit 1; }
mkdir -p "$OUT"
cd "$ROOT/apps/mobile"
xcodegen generate --spec project.yml
xcodebuild archive -project ChinaTextbookStudy.xcodeproj -scheme ChinaTextbookStudy \
  -configuration Release -destination 'generic/platform=iOS' \
  -derivedDataPath "$DERIVED" -archivePath "$ARCHIVE" \
  CODE_SIGNING_ALLOWED=NO CODE_SIGNING_REQUIRED=NO CODE_SIGN_IDENTITY='' \
  CURRENT_PROJECT_VERSION="${IOS_CLOUD_BUILD_NUMBER:-1}"
APP="$ARCHIVE/Products/Applications/ChinaTextbookStudy.app"
test -d "$APP"
STAGE="$(mktemp -d "$OUT/package.XXXXXX")"
trap 'rm -rf "$STAGE"' EXIT
mkdir "$STAGE/Payload"
ditto "$APP" "$STAGE/Payload/ChinaTextbookStudy.app"
ditto -c -k --keepParent "$STAGE/Payload" "$OUT/CongcongCloud-unsigned.ipa"
python3 - "$OUT/CongcongCloud-unsigned.ipa" <<'PY'
import plistlib,sys,zipfile
with zipfile.ZipFile(sys.argv[1]) as z:
    assert z.testzip() is None
    prefix='Payload/ChinaTextbookStudy.app/'
    info=plistlib.loads(z.read(prefix+'Info.plist'))
    assert info['CFBundleIdentifier']=='com.lacknb.study.cloudtest'
    assert 'iPhoneOS' in info['CFBundleSupportedPlatforms']
    assert info.get('NSMicrophoneUsageDescription')
    assert not info.get('NSAppTransportSecurity',{}).get('NSAllowsArbitraryLoads',False)
    assert z.read(prefix+info['CFBundleExecutable'])[:4] == bytes.fromhex('cffaedfe')
    forbidden=['seed-data.zip','seed-index.json','embedded.mobileprovision','_CodeSignature/']
    assert not any(any(part in name for part in forbidden) for name in z.namelist())
    assert not any('/data/books/' in name or '/private-content/' in name for name in z.namelist())
print('Validated unsigned iPhoneOS IPA: cloud target, microphone description, TLS, no offline answers/signing secrets.')
PY
(cd "$OUT" && shasum -a 256 CongcongCloud-unsigned.ipa > SHA256SUMS)
echo "IPA：$OUT/CongcongCloud-unsigned.ipa（未签名，安装前须自行签名）"
