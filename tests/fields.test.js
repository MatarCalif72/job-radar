// Run: node tests/fields.test.js
const assert = require("assert");
const J = require("../docs/fields.js");

// 1. auto-fill titles from a short answer
let r = J.suggestTitles("QA");
assert.deepStrictEqual(r.matched, ["QA / Testing"]);
for (const t of ["qa", "test automation", "sdet", "quality engineer"]) assert(r.titles.includes(t), t);

r = J.suggestTitles("DevOps, backend");
assert(r.titles.includes("sre") && r.titles.includes("backend"));
assert.strictEqual(r.matched.length, 2);

r = J.suggestTitles("data");  // fuzzy: several data fields
assert(r.matched.length >= 2 && r.titles.includes("data analyst"));

r = J.suggestTitles("underwater basket weaving");  // unknown -> uses the words
assert.deepStrictEqual(r.unknown, ["underwater basket weaving"]);
assert.deepStrictEqual(r.titles, ["underwater basket weaving"]);

assert.deepStrictEqual(J.suggestTitles("").titles, []);
assert.deepStrictEqual(J.suggestTitles("x").titles, []);  // too short to guess

// 2. levels
let l = J.levelLists("junior");
assert(l.boost.includes("junior") && l.exclude.includes("senior"));
l = J.levelLists("senior");
assert(l.boost.includes("senior") && l.exclude.includes("junior"));
l = J.levelLists("any");
assert.deepStrictEqual([l.boost, l.exclude], [[], []]);
l.boost.push("x");  // returned lists are copies
assert.deepStrictEqual(J.levelLists("any").boost, []);

// 3. locations
let loc = J.expandLocations("Tel Aviv");
assert(loc.includes("tel aviv") && loc.includes("ramat gan") && loc.includes("israel"));
loc = J.expandLocations("Tel Aviv", { includeIsrael: false });
assert(!loc.includes("israel"));
assert.deepStrictEqual(J.expandLocations("London"), ["london"]);          // not Israeli -> no "israel"
assert(J.expandLocations("Haifa, remote").includes("remote"));
assert(J.expandLocations("Israel").includes("israel"));
assert.deepStrictEqual(J.expandLocations(""), []);

// 4. settings + validation
const s = J.buildSettings({
  field: "QA", level: "junior", titles: ["qa", "qa"], boost: ["junior"], exclude: ["senior"],
  locations: ["israel"], skills: ["AWS", "Docker"], locText: "Israel", includeIsrael: true, remote: false,
});
assert.deepStrictEqual(s.titles, ["qa"]);  // de-duplicated
assert.strictEqual(s.version, 1);
assert.deepStrictEqual(J.validate(s), []);
assert.strictEqual(J.validate(J.buildSettings({ titles: [] })).length, 1);
assert.deepStrictEqual(J.splitList("AWS, Docker ,  AWS"), ["AWS", "Docker"]);  // keeps case

console.log("fields.test.js: all passed");
