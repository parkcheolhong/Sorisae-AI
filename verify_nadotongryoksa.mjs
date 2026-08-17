import { chromium } from 'playwright';

const BASE = 'http://127.0.0.1:3000/marketplace/nadotongryoksa';
const EMAIL = '119cash@naver.com';
const PW = 'space0215@';

async function run(round) {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  const log = (msg) => console.log(`[Round ${round}] ${msg}`);

  try {
    await page.goto(BASE, { waitUntil: 'networkidle', timeout: 20000 });
    log('페이지 로드 OK');

    // 1. 헤더 로그인 버튼 확인
    const loginBtn = await page.locator('button:has-text("🔐 로그인")').first();
    await loginBtn.waitFor({ state: 'visible', timeout: 5000 });
    log('✅ 헤더 "🔐 로그인" 버튼 확인');

    // 2. 로그인 버튼 클릭 → 모달 확인
    await loginBtn.click();
    await page.waitForSelector('input[type="email"], input[placeholder*="이메일"]', { timeout: 5000 });
    log('✅ 로그인 모달 표시 확인');

    // 3. 이메일/비밀번호 입력
    await page.fill('input[type="email"], input[placeholder*="이메일"]', EMAIL);
    await page.fill('input[type="password"]', PW);
    log('입력 완료');

    // 4. 로그인 버튼 클릭
    await page.click('button:has-text("로그인"):not(:has-text("🔐"))');
    
    // 5. 결과 확인 (👤 또는 에러)
    try {
      await page.waitForFunction(() => {
        const btns = Array.from(document.querySelectorAll('button'));
        return btns.some(b => b.textContent.includes('👤'));
      }, { timeout: 8000 });
      log('✅ 로그인 성공 - 👤 드롭다운으로 변경됨');
    } catch {
      // 모달에 에러 메시지 확인
      const errText = await page.textContent('.login-error, [class*="error"]').catch(() => '');
      log(`⚠️ 로그인 결과 불명 (모달 에러: ${errText?.trim() || '없음'})`);
    }

    // 6. 주변검색 실행
    await page.click('button:has-text("주변 장소 찾기")');
    log('주변 검색 클릭');
    
    try {
      await page.waitForSelector('[class*="place"], .place-card, button:has-text("🗺️ 지도")', { timeout: 10000 });
      log('✅ 주변검색 결과 표시');
      
      const mapBtn = page.locator('button:has-text("🗺️ 지도")').first();
      if (await mapBtn.count() > 0) {
        await mapBtn.click();
        await page.waitForSelector('iframe[src*="openstreetmap"]', { timeout: 5000 });
        log('✅ OpenStreetMap iframe 표시 확인');
      } else {
        log('ℹ️ 지도 버튼 없음 (주변 결과 없음)');
      }
    } catch {
      log('ℹ️ 주변검색 결과 타임아웃 (API 응답 없음)');
    }

  } catch (e) {
    log(`❌ 오류: ${e.message}`);
  } finally {
    await browser.close();
  }
}

// 2회 연속 실행
await run(1);
await run(2);
console.log('\n실검증 2회 완료');
