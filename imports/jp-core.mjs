// The browser distribution of JP Core's Japanese primitives: the 漢字【かんじ】
// notation, its renderers, reading alignment, and the sentence schema.
//
// This file is the canonical source for consumers that cannot run Python — a
// static PWA, a service worker, an extension. It mirrors jp_core.furigana,
// jp_core.reading, and jp_core.corpus, and every rule here is decided there
// first. A consumer copies this file; it does not fork it.
export const SCHEMA_VERSION = 2;

// The lookahead rejects an annotation with nothing in it; `stray` then removes
// it. A model emits 【】 when it declines to supply a reading, and letting it
// through puts literal brackets on screen and reads them aloud.
const notation = /([㐀-䶿一-鿿々\u{20000}-\u{3134F}]+)【(?!\s*】)([^】]+)】/gu;
const stray = /【[^】]*】/g;
// The same class `notation` accepts, for code that has to recognise a base run
// before there is a reading on it. If these two drift, a run one brackets is a
// run the other drops as a stray, and the reading disappears with no error.
//
// The supplementary span is ext-B through ext-G. 𠮟 (U+20B9F) is joyo and lives
// there, and a class stopping at U+9FFF dropped its reading exactly that way.
export const KANJI = /[㐀-䶿一-鿿々\u{20000}-\u{3134F}]/u;
const KANA = /^[ぁ-ゟー]+$/;
const escapeHtml = value => value.replace(/[&<>"']/g, ch => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[ch]));

// Furigana and the casual/polite pair are Japanese-only. Every other target
// gets one plain translation.
export function hasRegisters(code){return code==="ja"}
export function hasFurigana(code){return code==="ja"}
export const DEFAULT_PAIR = {sourceLang:"en",targetLang:"ja"};

export function normalizeFurigana(value = "") {
  let out = "", offset = 0;
  for (const match of value.matchAll(notation)) {
    out += value.slice(offset, match.index).replace(stray, "");
    out += match[0];
    offset = match.index + match[0].length;
  }
  return out + value.slice(offset).replace(stray, "");
}

export function stripFurigana(value = "") {
  return value.replace(stray, "");
}

export function rubySegments(value = "") {
  value = normalizeFurigana(value);
  const segments = [];
  let offset = 0;
  for (const match of value.matchAll(notation)) {
    if (match.index > offset) segments.push({text: value.slice(offset, match.index)});
    segments.push({text: match[1], reading: match[2]});
    offset = match.index + match[0].length;
  }
  if (offset < value.length) segments.push({text: value.slice(offset)});
  return segments;
}

export function segmentHtml(segment) {
  return segment.reading
    ? "<ruby>" + escapeHtml(segment.text) + "<rt>" + escapeHtml(segment.reading) + "</rt></ruby>"
    : escapeHtml(segment.text);
}

export function rubyHtml(value = "") {
  return rubySegments(value).map(segmentHtml).join("");
}

// --- reading generation ------------------------------------------------------
// The browser twin of jp_core.reading. A reading is a dictionary lookup, not a
// generation task, so these place a reading an analyser supplied and never
// invent one: anything that does not line up is emitted bare.

// ァ..ヴ only. ヵ and ヶ sit at the top of the katakana block but have no
// hiragana anyone writes, and 一ヶ月 would come back as 一ゖ月.
export function toHiragana(value = "") {
  return value.replace(/[ァ-ヴ]/g, ch => String.fromCharCode(ch.charCodeAt(0) - 0x60));
}

// Compounds an analyser gets wrong because it segments them, and segmenting
// loses the sound change that only exists across the seam. Kept in step with
// jp_core.reading.PRONUNCIATION_OVERRIDES; 十分 is absent from both because it
// is じゅっぷん as a duration and じゅうぶん as "enough".
export const PRONUNCIATION_OVERRIDES = {
  "一回":"いっかい","一階":"いっかい","一個":"いっこ","一冊":"いっさつ","一歳":"いっさい",
  "一足":"いっそく","一点":"いってん","一杯":"いっぱい","一匹":"いっぴき","一分":"いっぷん",
  "一本":"いっぽん","一泊":"いっぱく","一枚":"いちまい","一週間":"いっしゅうかん",
  "一生":"いっしょう","一緒":"いっしょ",
  "六回":"ろっかい","六階":"ろっかい","六個":"ろっこ","六本":"ろっぽん","六匹":"ろっぴき",
  "六杯":"ろっぱい","六分":"ろっぷん",
  "八回":"はっかい","八階":"はっかい","八個":"はっこ","八本":"はっぽん","八匹":"はっぴき",
  "八杯":"はっぱい","八分":"はっぷん","八冊":"はっさつ",
  "十回":"じゅっかい","十階":"じゅっかい","十個":"じゅっこ","十本":"じゅっぽん",
  "十匹":"じゅっぴき","十杯":"じゅっぱい","十冊":"じゅっさつ","十歳":"じゅっさい",
  "三本":"さんぼん","三匹":"さんびき","三杯":"さんばい","三階":"さんがい","三分":"さんぷん",
  "三百":"さんびゃく","三千":"さんぜん",
  "何本":"なんぼん","何匹":"なんびき","何杯":"なんばい","何階":"なんがい","何分":"なんぷん",
  "何回":"なんかい",
  "日本":"にほん"
};

// Walk base and reading in step, handing each kanji run whatever lies between
// the kana runs that bracket it: 話し合う / はなしあう pins し at index 2 and
// う at 4, which leaves はな for 話 and あ for 合. Returns null when the two do
// not line up rather than splitting the difference.
export function alignReading(base, reading) {
  if (!base || !reading || !KANA.test(reading)) return null;
  const runs = [];
  for (const ch of base) {
    const kanji = KANJI.test(ch);
    const last = runs[runs.length - 1];
    if (last && last.kanji === kanji) last.text += ch;
    else runs.push({kanji, text: ch});
  }
  if (!runs.some(run => run.kanji)) return [{text: base}];
  const segments = [];
  let pos = 0;
  for (let i = 0; i < runs.length; i++) {
    const run = runs[i];
    if (!run.kanji) {
      if (!reading.startsWith(run.text, pos)) return null;
      segments.push({text: run.text});
      pos += run.text.length;
      continue;
    }
    const next = runs[i + 1];
    // Every kanji run needs at least one kana of its own, hence pos + 1.
    const end = next ? reading.indexOf(next.text, pos + 1) : reading.length;
    if (end < 0 || end <= pos) return null;
    segments.push({text: run.text, reading: reading.slice(pos, end)});
    pos = end;
  }
  return pos === reading.length ? segments : null;
}

// The inverse of rubySegments: tokens back out as notation.
export function segmentsToNotation(segments = []) {
  return segments.map(part => part.reading ? `${part.text}【${part.reading}】` : part.text).join("");
}

// Merge adjacent tokens whose joined surface has a known reading, so an
// override can repair a compound the analyser split.
function applyOverrides(tokens, overrides) {
  const keys = Object.keys(overrides);
  if (!keys.length) return tokens;
  const longest = Math.max(...keys.map(key => key.length));
  const out = [];
  for (let i = 0; i < tokens.length; i++) {
    let joined = "", match = null;
    for (let span = i; span < tokens.length; span++) {
      joined += tokens[span][0];
      if (joined.length > longest) break;
      if (overrides[joined]) match = [span, joined, overrides[joined]];
    }
    if (match) { out.push([match[1], match[2]]); i = match[0]; }
    else out.push(tokens[i]);
  }
  return out;
}

// tokens: [[surface, reading], ...] from a morphological analyser, the reading
// in kana or empty. Returns canonical notation.
export function readingsToNotation(tokens, overrides = {}) {
  let out = "";
  for (const [surface, reading] of applyOverrides([...tokens], {...PRONUNCIATION_OVERRIDES, ...overrides})) {
    const kana = reading && reading !== "*" ? toHiragana(reading) : "";
    const segments = kana ? alignReading(surface, kana) : null;
    out += segments ? segmentsToNotation(segments) : surface;
  }
  return out;
}

// --- sentences ---------------------------------------------------------------

export function validateTranslation(result, targetLang = "ja") {
  const japanese = normalizeFurigana(String(result?.japanese || "").trim());
  // Only Japanese can be script-checked this cheaply. For everything else a
  // non-empty answer is all we can honestly assert.
  if (!japanese) throw new Error("The translator returned nothing.");
  if (targetLang === "ja" && !/[぀-ヿ㐀-鿿]/.test(japanese)) throw new Error("The translator did not return a Japanese sentence.");
  return japanese;
}

export function validateTranslations(result, targetLang = "ja") {
  const casual = validateTranslation({japanese:result?.casual || result?.casualJapanese || result?.translation || result?.japanese}, targetLang);
  if (!hasRegisters(targetLang)) return {casual,polite:casual};
  const polite = validateTranslation({japanese:result?.polite || result?.politeJapanese || result?.japanese || result?.casualJapanese}, targetLang);
  return {casual,polite};
}

// crypto.randomUUID is secure-context only, so it is simply missing over
// plain http — a custom domain before its certificate lands, a LAN address,
// a file:// open. getRandomValues has no such restriction, so the id comes
// from there and randomUUID is only a shortcut when it exists.
export function newId(){
  if(typeof crypto!=="undefined"&&crypto.randomUUID)return crypto.randomUUID();
  const bytes=new Uint8Array(16);
  if(typeof crypto!=="undefined"&&crypto.getRandomValues)crypto.getRandomValues(bytes);
  else for(let i=0;i<16;i++)bytes[i]=Math.floor(Math.random()*256);
  bytes[6]=(bytes[6]&0x0f)|0x40;bytes[8]=(bytes[8]&0x3f)|0x80;
  const hex=[...bytes].map(b=>b.toString(16).padStart(2,"0")).join("");
  return `${hex.slice(0,8)}-${hex.slice(8,12)}-${hex.slice(12,16)}-${hex.slice(16,20)}-${hex.slice(20)}`;
}

export function createSentence(source, translation, now = new Date(), id = newId(), pair = DEFAULT_PAIR) {
  const {sourceLang,targetLang}={...DEFAULT_PAIR,...pair};
  const forms=typeof translation==="string"?{casual:translation,polite:translation}
    :{casual:translation.casual??translation.casualJapanese,polite:translation.polite??translation.politeJapanese??translation.casual??translation.casualJapanese};
  const casual=forms.casual.trim(),polite=(forms.polite||forms.casual).trim();
  return {id,sourceLang,targetLang,
    source:source.trim(),target:casual,plainTarget:stripFurigana(casual).trim(),
    casualTarget:casual,plainCasualTarget:stripFurigana(casual).trim(),
    politeTarget:polite,plainPoliteTarget:stripFurigana(polite).trim(),
    echoCount:0,createdAt:now.toISOString(),updatedAt:now.toISOString(),
    translationProvider:"deepseek",schemaVersion:SCHEMA_VERSION};
}

// Replace the linguistic content of an existing card without resetting its history.
export function replaceSentenceContent(record, {source,casual,polite}, now = new Date()) {
  if (!source?.trim() || !casual?.trim()) throw new Error("A sentence and its meaning are required.");
  const fresh=createSentence(source,{casual:normalizeFurigana(casual),polite:normalizeFurigana(polite||casual)},now,record.id,record);
  const keys=["source","target","plainTarget","casualTarget","plainCasualTarget","politeTarget","plainPoliteTarget","updatedAt"];
  return {...record,...Object.fromEntries(keys.map(key=>[key,fresh[key]]))};
}

// Records written before languages existed were all English to Japanese. The
// old field names are kept readable here rather than anywhere else: every
// other reader works from the neutral ones.
export function migrateSentence(record) {
  if (!record || record.schemaVersion >= SCHEMA_VERSION) return record;
  const casual=record.casualJapanese||record.japanese||"";
  const polite=record.politeJapanese||casual;
  const {english,japanese,plainJapanese,casualJapanese,plainCasualJapanese,politeJapanese,plainPoliteJapanese,...rest}=record;
  return {...rest,sourceLang:"en",targetLang:"ja",
    source:english||"",target:casual,plainTarget:plainJapanese||stripFurigana(casual).trim(),
    casualTarget:casual,plainCasualTarget:plainCasualJapanese||stripFurigana(casual).trim(),
    politeTarget:polite,plainPoliteTarget:plainPoliteJapanese||stripFurigana(polite).trim(),
    schemaVersion:SCHEMA_VERSION};
}

// Identity ignores furigana and Japanese layout whitespace, but keeps languages
// and wording distinct. Import IDs are not sufficient to identify the same text.
export function sentenceIdentity(record) {
  const s=migrateSentence(record);if(!s?.target)return "";
  const lang=s.targetLang||DEFAULT_PAIR.targetLang;
  const plain=stripFurigana(s.casualTarget||s.target).normalize("NFKC").trim();
  const text=lang==="ja"?plain.replace(/\s+/g,""):plain.replace(/\s+/g," ");
  return JSON.stringify([s.sourceLang||DEFAULT_PAIR.sourceLang,lang,text]);
}

export function mergeSentences(current, incoming) {
  const merged = new Map(current.map(migrateSentence).filter(Boolean).map(item => [item.id, item]));
  const identities=new Map([...merged.values()].map(s=>[sentenceIdentity(s),s.id]));
  const union=(a,b)=>[...new Set([...(Array.isArray(a)?a:[]),...(Array.isArray(b)?b:[])])];
  for (const record of incoming) {
    const candidate = migrateSentence(record);
    if (!candidate?.id || !candidate.source || !candidate.target) continue;
    const identity=sentenceIdentity(candidate),sameId=merged.has(candidate.id),id=sameId?candidate.id:identities.get(identity);
    const old = merged.get(id);
    if (!old) { merged.set(candidate.id, candidate);identities.set(identity,candidate.id);continue; }
    // A catalogue refresh must never replace the learner's card or scheduling.
    const newest=sameId&&Date.parse(candidate.updatedAt)>Date.parse(old.updatedAt)?candidate:old;
    const reviews=[...new Map([...(old.reviews||[]),...(candidate.reviews||[])].map(r=>[JSON.stringify(r),r])).values()].sort((a,b)=>String(a.at).localeCompare(String(b.at)));
    const result={...old,...newest,id:old.id,
      echoCount:Math.max(Number(old.echoCount)||0,Number(candidate.echoCount)||0),
      createdAt:Date.parse(old.createdAt)<=Date.parse(candidate.createdAt)?old.createdAt:candidate.createdAt,
      ...(Array.isArray(old.grammar)||Array.isArray(candidate.grammar)?{grammar:union(old.grammar,candidate.grammar)}:{}),
      ...(Array.isArray(old.vocabulary)||Array.isArray(candidate.vocabulary)?{vocabulary:union(old.vocabulary,candidate.vocabulary)}:{})};
    if(reviews.length)result.reviews=reviews;
    if(old.srs&&(!candidate.srs||Number(candidate.srs.reps||0)<Number(old.srs.reps||0)))result.srs=old.srs;
    if(!sameId&&old.srs)result.srs=old.srs;
    if(old.reviewTrack)result.reviewTrack=old.reviewTrack;
    const analysis=[...new Map([...(candidate.grammarAnalysis||[]),...(old.grammarAnalysis||[])].map(a=>[a.text,a])).values()];if(analysis.length)result.grammarAnalysis=analysis;
    merged.set(old.id,result);identities.set(identity,old.id);
  }
  return [...merged.values()];
}

export function exportBackup(sentences, preferences = {}) {
  const {apiKey, providerKeys, ...safe} = preferences;
  return {schemaVersion:SCHEMA_VERSION,exportedAt:new Date().toISOString(),sentences,preferences:safe};
}

// --- mnemonic mora alphabet v1 ----------------------------------------------
export const MORA_MNEMONICS_VERSION = 2;
export const MORA_MNEMONICS = Object.freeze({"あ":"飴","い":"犬","う":"牛","え":"海老","お":"お茶","か":"傘","き":"木","く":"熊","け":"剣","こ":"氷","さ":"猿","し":"鹿","す":"寿司","せ":"蝉","そ":"算盤","た":"太鼓","ち":"蝶々","つ":"机","て":"手","と":"鳥","な":"茄子","に":"肉","ぬ":"縫い針","ね":"猫","の":"鋸","は":"花","ひ":"火","ふ":"船","へ":"蛇","ほ":"本","ま":"枕","み":"水","む":"虫","め":"目","も":"餅","や":"山","ゆ":"雪","よ":"洋服","ら":"ライオン","り":"林檎","る":"ルーペ","れ":"冷蔵庫","ろ":"ロケット","わ":"鰐","を":"ヲタ芸","ん":"「ん？」"});
export const MORA_MNEMONIC_MODIFIERS = Object.freeze({dakuten:"泥 — cover the base anchor in mud (濁る → muddy/cloudy)",handakuten:"泡 — cover the base anchor in bubbles",yoon:"ゃ・ゅ・ょ — fuse with the preceding い-row mora; combine that anchor with 山・雪・洋服 into one image",sokuon:"っ — no anchor of its own; tighten/double the next consonant by showing the next anchor twice",n:"「ん？」 — a questioning reaction",wo:"ヲタ芸 — energetic dancing with glowing light sticks"});
export function moraMnemonicTable(){return Object.entries(MORA_MNEMONICS).map(([mora,image])=>({mora,image}))}
const MORA_VOICED=Object.freeze({"が":["か","泥"],"ぎ":["き","泥"],"ぐ":["く","泥"],"げ":["け","泥"],"ご":["こ","泥"],"ざ":["さ","泥"],"じ":["し","泥"],"ず":["す","泥"],"ぜ":["せ","泥"],"ぞ":["そ","泥"],"だ":["た","泥"],"ぢ":["ち","泥"],"づ":["つ","泥"],"で":["て","泥"],"ど":["と","泥"],"ば":["は","泥"],"び":["ひ","泥"],"ぶ":["ふ","泥"],"べ":["へ","泥"],"ぼ":["ほ","泥"],"ぱ":["は","泡"],"ぴ":["ひ","泡"],"ぷ":["ふ","泡"],"ぺ":["へ","泡"],"ぽ":["ほ","泡"]});
const MORA_SMALL_Y=Object.freeze({"ゃ":"や","ゅ":"ゆ","ょ":"よ"});
const MORA_YOON_BASES=new Set(["き","ぎ","し","じ","ち","ぢ","に","ひ","び","ぴ","み","り"]);
function moraAnchor(mora){if(MORA_MNEMONICS[mora])return MORA_MNEMONICS[mora];const mod=MORA_VOICED[mora];return mod?mod[1]+"の"+MORA_MNEMONICS[mod[0]]:""}
export function moraMnemonicTokens(reading=""){
  const kana=[...toHiragana(String(reading).normalize("NFKC"))],out=[];
  let sokuon=false;
  for(let i=0;i<kana.length;i++){
    const current=kana[i];
    if(current==="っ"){sokuon=true;continue}
    let image=moraAnchor(current),mora=current;
    if(!image)continue;
    const small=MORA_SMALL_Y[kana[i+1]];
    if(small&&MORA_YOON_BASES.has(current)){mora+=kana[++i];image+="＋"+MORA_MNEMONICS[small]+"（融合）"}
    if(sokuon){mora="っ"+mora;image+="×2（っ：次の子音を詰める）";sokuon=false}
    out.push({mora,image})
  }
  return out
}
export function moraMnemonicPrompt(){const rows=Object.entries(MORA_MNEMONICS).map(([m,i])=>m+"="+i).join(", ");return "Echo Mora (canonical; never substitute another anchor): "+rows+".\nVoiced kana use the unvoiced anchor covered in 泥: が=泥の傘, ぎ=泥の木, ぐ=泥の熊, げ=泥の剣, ご=泥の氷; likewise ざ/だ/ば rows. P sounds use the は-row anchor covered in 泡: ぱ=泡の花, ぴ=泡の火, ぷ=泡の船, ぺ=泡の蛇, ぽ=泡の本.\nSmall ゃ/ゅ/ょ are fused, never separate mnemonic beats: combine the preceding い-row anchor with 山/雪/洋服 into one image, e.g. きゃ=木＋山, しゅ=鹿＋雪, ちょ=蝶々＋洋服. Small っ has no anchor of its own: it tightens/doubles the following consonant, so show the following anchor twice/overlapped, e.g. きって=木 then 手×2.\nUse these only as a rescue mnemonic. Make the shortest vivid causal animation you can: the anchor objects must appear in pronunciation order, physically interacting so replaying the movement recovers the mora order. The central action/consequence must embody the Japanese meaning itself, not an English sound-alike. Prefer touch, force, motion, sound and consequence over explanation. Do not add a memory palace or location. Do not invent a canonical anchor for ー or other sounds not defined here. End by reconnecting the scene directly to the Japanese word so the mnemonic can fade with practice."}
