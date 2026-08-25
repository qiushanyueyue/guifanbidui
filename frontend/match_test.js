// Simulate the match logic from ComparisonTable.tsx

const calculateMatchScore = (sourceName, sourceCode, result) => {
    if (!result) return { score: "-", isConsistent: "-" };

    let score = 0;
    // Normalize codes: uppercase and remove ALL spaces
    const normSourceCode = sourceCode.replace(/\s+/g, '').toUpperCase();
    const normResultCode = result.code.replace(/\s+/g, '').toUpperCase();

    const normSourceName = sourceName.trim();
    const normResultName = result.name.trim();

    // 1. Code Match (High Weight)
    if (normSourceCode === normResultCode) {
        score += 50;
    } else if (normResultCode.includes(normSourceCode) || normSourceCode.includes(normResultCode)) {
        score += 30; // Partial code match
    }

    // 2. Name Match
    if (normSourceName === normResultName) {
        score += 30;
    } else {
        // Simple overlap check
        let matchCount = 0;
        for (let char of normSourceName) {
            if (normResultName.includes(char)) matchCount++;
        }
        const similarity = matchCount / Math.max(normSourceName.length, normResultName.length);
        if (similarity > 0.8) score += 20;
        else if (similarity > 0.5) score += 10;
    }

    // 3. Year/Version Match
    const versionRegex = /[（(](.*?)[)）]/g;
    const sourceVersions = [...sourceName.matchAll(versionRegex)].map(m => m[1]);

    let versionMismatch = false;
    if (sourceVersions.length > 0) {
        for (const ver of sourceVersions) {
            if (!result.name.includes(ver)) {
                versionMismatch = true;
                break;
            }
        }
    }

    if (!versionMismatch) {
        score += 20;
    } else {
        score = Math.min(score, 90);
    }

    if (score >= 100) return { score: "100%", isConsistent: "与匹配规范一致" };
    if (versionMismatch) return { score: `${Math.min(score, 90)}%`, isConsistent: "年份/版本不一致" };
    if (normSourceCode !== normResultCode) return { score: `${score}%`, isConsistent: "编号不一致" };
    if (normSourceName !== normResultName) return { score: `${score}%`, isConsistent: "名称不一致" };

    return { score: `${score}%`, isConsistent: "部分匹配" };
};

// Test Case
const inputName = "地铁设计规范";
const inputCode = "GB50157-2013";

const result = {
    code: "GB 50157-2013",
    name: "地铁设计规范",
    status: "unknown"
};

const output = calculateMatchScore(inputName, inputCode, result);
console.log(`Input: ${inputCode} vs Result: ${result.code}`);
console.log(`Match Score: ${output.score}`);
console.log(`Is Compatible: ${output.isConsistent}`);

if (output.score === "100%") {
    console.log("SUCCESS");
} else {
    console.log("FAILURE");
}
