// [기능 분리 Phase5.2] 소리새AI 기능 — 자기에코 판정 순수 헬퍼(자족적, App 상태 비의존).
// App.tsx 모놀리스에서 추출. 'TTS 답변'이 마이크로 되돌아온 전사(STT)와 같은 발화인지
// 모양만으로 비교해 무한 자문자답 루프를 끊는다(언어 무관, CJK/라틴 공통).

/**
 * 소리새 AI 자기에코 비교용 정규화 — 공백·구두점을 제거해 'TTS 답변'이 마이크로 되돌아온
 * 전사(STT)와 같은 발화인지 모양만으로 비교한다(언어 무관, CJK/라틴 공통).
 */
export function normalizeEchoText(text: string): string {
    return String(text || '')
        .toLowerCase()
        .replace(/[\s.,!?;:'"`()\[\]{}~\-·…‥。、！？；：「」『』，．（）【】〔〕《》]+/g, '')
        .trim();
}

/**
 * 두 정규화 문자열의 겹침 비율(0~1). 한쪽이 다른쪽을 포함하면 1, 아니면 문자 bigram Dice 계수.
 * 임계 이상이면 '자기 음성 에코'로 판정해 무한 자문자답 루프를 끊는다.
 */
export function echoOverlapRatio(a: string, b: string): number {
    if (!a || !b) return 0;
    const shorter = a.length <= b.length ? a : b;
    const longer = a.length <= b.length ? b : a;
    if (longer.includes(shorter)) return 1;
    const bigrams = (s: string): Set<string> => {
        const set = new Set<string>();
        for (let i = 0; i < s.length - 1; i += 1) set.add(s.slice(i, i + 2));
        return set;
    };
    const setA = bigrams(a);
    const setB = bigrams(b);
    if (!setA.size || !setB.size) return 0;
    let intersection = 0;
    setA.forEach((g) => { if (setB.has(g)) intersection += 1; });
    const dice = (2 * intersection) / (setA.size + setB.size);
    // 비대칭 포함도: 마이크가 '긴 답변'의 앞부분만 max_duration(약 12초)으로 잘라 잡으면
    // 부분 전사라 Dice(대칭)는 ~0.67로 임계 밑에 떨어져 에코를 놓친다. 짧은 쪽(부분 에코)이
    // 긴 쪽(원 답변)에 거의 포함되면 포함도≈1 → 부분 에코도 확실히 잡아 무한 자문자답을 끊는다.
    const containment = intersection / Math.min(setA.size, setB.size);
    return Math.max(dice, containment);
}
