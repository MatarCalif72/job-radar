/* Logic for the "Redefine jobs" page: turns short answers into search settings.
   Works in the browser and in Node (for tests). No dependencies. */
(function (root) {
  "use strict";

  const SENIOR = ["senior", "sr", "staff", "principal", "lead", "leader", "head of", "director", "manager", "architect", "vp", "expert"];
  const JUNIOR = ["junior", "jr", "entry level", "entry-level", "graduate", "student", "intern", "internship"];

  const LEVELS = {
    junior: { label: "Junior / student", boost: JUNIOR, exclude: SENIOR },
    mid: { label: "Mid level", boost: [], exclude: SENIOR.concat(["intern", "internship", "student"]) },
    senior: { label: "Senior", boost: ["senior", "sr", "staff", "lead", "principal"], exclude: JUNIOR },
    any: { label: "Any level", boost: [], exclude: [] },
  };

  // name, words people might type (aliases), and the job titles to look for
  const FIELDS = [
    { name: "QA / Testing",
      aliases: ["qa", "quality", "quality assurance", "test", "testing", "tester", "sdet", "test automation", "automation"],
      titles: ["qa", "test automation", "sdet", "quality engineer", "quality assurance", "software tester"] },
    { name: "DevOps / Cloud",
      aliases: ["devops", "dev ops", "sre", "cloud", "infrastructure", "platform", "site reliability"],
      titles: ["devops", "dev ops", "sre", "site reliability", "platform engineer", "cloud engineer", "infrastructure engineer", "release engineer"] },
    { name: "Backend",
      aliases: ["backend", "back-end", "back end", "server side", "software engineer", "software developer", "developer", "programmer"],
      titles: ["backend", "back-end", "back end", "software engineer", "software developer", "server side"] },
    { name: "Frontend",
      aliases: ["frontend", "front-end", "front end", "web developer", "react"],
      titles: ["frontend", "front-end", "front end", "web developer", "react developer", "ui developer"] },
    { name: "Full stack",
      aliases: ["full stack", "fullstack", "full-stack"],
      titles: ["full stack", "fullstack", "full-stack", "software engineer", "software developer"] },
    { name: "Mobile",
      aliases: ["mobile", "ios", "android", "react native", "flutter"],
      titles: ["mobile", "ios", "android", "react native", "flutter"] },
    { name: "Data analyst / BI",
      aliases: ["data analyst", "analyst", "bi", "business intelligence", "analytics", "data analysis"],
      titles: ["data analyst", "bi analyst", "bi developer", "business intelligence", "analytics", "product analyst"] },
    { name: "Data engineering",
      aliases: ["data engineer", "data engineering", "etl", "big data", "data platform"],
      titles: ["data engineer", "etl", "big data", "data platform"] },
    { name: "Data science / ML / AI",
      aliases: ["data scientist", "data science", "machine learning", "ml", "ai", "deep learning", "nlp"],
      titles: ["data scientist", "machine learning", "ml engineer", "ai engineer", "deep learning", "nlp", "computer vision"] },
    { name: "Security",
      aliases: ["security", "cyber", "cybersecurity", "infosec", "appsec", "soc"],
      titles: ["security", "cyber", "soc analyst", "penetration", "appsec", "infosec"] },
    { name: "IT / Helpdesk / Sysadmin",
      aliases: ["it", "helpdesk", "help desk", "it support", "sysadmin", "system administrator", "systems administrator", "network"],
      titles: ["it support", "help desk", "helpdesk", "system administrator", "sysadmin", "it engineer", "it technician", "it administrator", "desktop support", "it specialist", "network engineer",
        "it system", "it systems", "it infrastructure", "it operations", "service desk", "technical support"] },
    { name: "Product management",
      aliases: ["product", "product manager", "product owner", "pm"],
      titles: ["product manager", "product owner", "product operations"] },
    { name: "Project / Program management",
      aliases: ["project manager", "program manager", "project management", "delivery", "scrum"],
      titles: ["project manager", "program manager", "delivery manager", "scrum master"] },
    { name: "UX / UI design",
      aliases: ["ux", "ui", "ux/ui", "design", "designer", "product design", "graphic design"],
      titles: ["ux", "ui designer", "product designer", "ux/ui", "graphic designer", "visual designer"] },
    { name: "Customer support / success",
      aliases: ["support", "customer support", "customer success", "customer service", "technical support"],
      titles: ["customer success", "customer support", "technical support", "support engineer", "support specialist", "customer service"] },
    { name: "Sales / Business development",
      aliases: ["sales", "sdr", "bdr", "business development", "account executive"],
      titles: ["sales", "sdr", "bdr", "business development", "account executive", "account manager"] },
    { name: "Solutions / Pre-sales",
      aliases: ["solutions engineer", "pre-sales", "presales", "sales engineer", "implementation", "technical account manager"],
      titles: ["solutions engineer", "sales engineer", "implementation", "technical account manager", "customer engineer"] },
    { name: "Marketing",
      aliases: ["marketing", "content", "seo", "growth", "social media"],
      titles: ["marketing", "content", "seo", "growth", "social media", "performance marketing"] },
    { name: "Embedded / Hardware",
      aliases: ["embedded", "firmware", "hardware", "fpga", "verification"],
      titles: ["embedded", "firmware", "hardware engineer", "fpga", "verification engineer"] },
    { name: "Game development",
      aliases: ["game", "games", "game dev", "unity", "unreal"],
      titles: ["game developer", "unity", "unreal", "game designer"] },
    { name: "Technical writing",
      aliases: ["technical writer", "technical writing", "documentation"],
      titles: ["technical writer", "documentation"] },
    { name: "HR / Recruiting",
      aliases: ["hr", "recruiter", "recruiting", "talent", "people operations"],
      titles: ["recruiter", "talent acquisition", "hr", "people operations"] },
  ];

  const TEL_AVIV_AREA = ["tel aviv", "tel-aviv", "ramat gan", "givatayim", "herzliya", "petah tikva", "petach tikva",
    "holon", "bnei brak", "rishon", "rehovot", "or yehuda", "kfar saba", "raanana", "ra'anana", "netanya", "hod hasharon", "bat yam"];

  const PLACES = [
    { keys: ["israel", "anywhere in israel", "all israel"], list: ["israel"], israeli: true },
    { keys: ["tel aviv", "tel-aviv", "tlv", "gush dan", "center", "central israel", "tel aviv area"], list: TEL_AVIV_AREA, israeli: true },
    { keys: ["sharon", "herzliya", "netanya", "kfar saba", "raanana"], list: ["herzliya", "netanya", "kfar saba", "raanana", "ra'anana", "hod hasharon"], israeli: true },
    { keys: ["haifa", "north", "the north"], list: ["haifa", "yokneam", "nazareth", "karmiel", "tiberias", "afula"], israeli: true },
    { keys: ["jerusalem"], list: ["jerusalem"], israeli: true },
    { keys: ["beer sheva", "be'er sheva", "beersheba", "south", "the south"], list: ["beer sheva", "be'er sheva", "beersheba", "ashdod", "ashkelon", "eilat"], israeli: true },
  ];

  function uniq(arr) {
    const seen = new Set();
    return (arr || []).filter((x) => (seen.has(x) ? false : (seen.add(x), true)));
  }

  // "QA, DevOps and backend" -> ["qa", "devops", "backend"]
  function splitTerms(text) {
    return String(text || "").split(/[,;\n&]|\band\b/i).map((t) => t.trim().toLowerCase()).filter((t) => t.length >= 2);
  }

  // keeps the user's capitalisation (for skills like "AWS")
  function splitList(text) {
    return uniq(String(text || "").split(/[,;\n]/).map((t) => t.trim()).filter(Boolean));
  }

  function findFields(term) {
    const exact = FIELDS.filter((f) => f.aliases.includes(term) || f.name.toLowerCase() === term);
    if (exact.length) return exact.slice(0, 1);
    return FIELDS.filter((f) =>
      f.name.toLowerCase().includes(term) ||
      f.aliases.some((a) => a.startsWith(term) || (a.length >= 3 && term.startsWith(a)) || (term.length >= 3 && a.includes(term)))
    ).slice(0, 3);
  }

  function suggestTitles(input) {
    const titles = [], matched = [], unknown = [];
    for (const term of splitTerms(input)) {
      const found = findFields(term);
      if (found.length) {
        for (const f of found) { titles.push(...f.titles); matched.push(f.name); }
      } else {
        titles.push(term);
        unknown.push(term);
      }
    }
    return { titles: uniq(titles), matched: uniq(matched), unknown: uniq(unknown) };
  }

  function levelLists(level) {
    const l = LEVELS[level] || LEVELS.junior;
    return { boost: l.boost.slice(), exclude: l.exclude.slice() };
  }

  function expandLocations(text, opts) {
    const o = Object.assign({ includeIsrael: true, remote: false }, opts || {});
    const out = [];
    let israeli = false, remote = !!o.remote;
    for (const term of splitTerms(text)) {
      if (term === "remote") { remote = true; continue; }
      const p = PLACES.find((x) => x.keys.includes(term));
      if (p) { out.push(...p.list); israeli = israeli || p.israeli; } else { out.push(term); }
    }
    if (israeli && o.includeIsrael) out.push("israel"); // jobs listed only as "Israel"
    if (remote) out.push("remote");
    return uniq(out);
  }

  function buildSettings(st) {
    return {
      version: 1,
      field: st.field || "",
      level: st.level || "junior",
      location_text: st.locText || "",
      include_israel: st.includeIsrael !== false,
      remote: !!st.remote,
      titles: uniq(st.titles),
      exclude_titles: uniq(st.exclude),
      boost_titles: uniq(st.boost),
      locations: uniq(st.locations),
      skills: uniq(st.skills),
      include_unknown_location: false,
    };
  }

  function validate(s) {
    const problems = [];
    if (!s.titles.length) problems.push("Add at least one job title (question 1).");
    return problems;
  }

  const api = { LEVELS, FIELDS, suggestTitles, levelLists, expandLocations, buildSettings, validate, splitTerms, splitList, uniq };
  root.JobRadar = api;
  if (typeof module === "object" && module.exports) module.exports = api;
})(typeof globalThis !== "undefined" ? globalThis : this);
