const TZ = "Asia/Seoul";

function getSeoulDate() {
  const now = new Date();
  const seoul = new Date(now.toLocaleString("en-US", { timeZone: TZ }));
  if (seoul.getHours() < 7) seoul.setDate(seoul.getDate() - 1);
  return seoul.toISOString().slice(0, 10);
}

function seededRandom(seed) {
  let h = 2166136261;
  for (let i = 0; i < seed.length; i++) {
    h ^= seed.charCodeAt(i);
    h += (h << 1) + (h << 4) + (h << 7) + (h << 8) + (h << 24);
  }
  return () => (h = Math.imul(48271, h) % 2147483647) / 2147483647;
}

async function loadTodayCards() {
  const res = await fetch("./cards.json");
  const cards = await res.json();

  const seed = getSeoulDate();
  const rand = seededRandom(seed);

  const enShort = cards.filter(c => c.lang === "en" && c.length === "short");
  const enLong  = cards.filter(c => c.lang === "en" && c.length === "long");
  const jpN3    = cards.filter(c => c.lang === "jp" && (c.level || "").startsWith("N3"));

  // 🔎 디버그(현재 데이터 개수 확인)
  console.log({ seed, enShort: enShort.length, enLong: enLong.length, jpN3: jpN3.length });

  const pick = (arr, label) => {
    if (!arr.length) {
      throw new Error(`No candidates for ${label}. Check cards.json values.`);
    }
    return arr[Math.floor(rand() * arr.length)];
  };

  const today = [
    pick(enShort, "en short"),
    pick(enLong, "en long"),
    pick(jpN3, "jp N3+")
  ];

  render(today);
}

function render(cards) {
  const root = document.getElementById("cards");
  root.innerHTML = "";

  cards.forEach(c => {
    const el = document.createElement("div");
    el.className = "card";
    el.innerHTML = `
      <h2>${c.word}</h2>
      <p class="situation">상황: ${c.situation}</p>
      <p class="example">예: ${c.example}</p>
      <p class="sentence">→ ${c.sentence}</p>
      <p class="meaning">뜻: ${c.meaning}</p>
    `;
    root.appendChild(el);
  });
}

loadTodayCards().catch(err => {
  console.error(err);
  document.getElementById("cards").innerHTML =
    `<div class="card"><h2>데이터 오류</h2><p>${err.message}</p></div>`;
});
