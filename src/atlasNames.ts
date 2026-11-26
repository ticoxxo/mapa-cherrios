// Invented, old-tongue-sounding names for the Atlas skin. They are pure decoration made from our own
// syllables (not any real or fictional language) and always shown with a plain-Spanish gloss beside them.
// The real neighbourhood name stays visible wherever it was before.
import type { Realm } from './data'
import { shortName } from './i18n'
import type { Skin } from './skin'

// Soft, flowing syllables (lots of vowels and liquids) so the names sound old and elvish-ish,
// but every piece is ours: combinations are checked against the deny-lists below.
const HEAD = ['Ae', 'Ela', 'Ilo', 'Lae', 'Mira', 'Nae', 'Sae', 'Thia', 'Vae', 'Ylla', 'Cae', 'Fae', 'Lio', 'Ona', 'Rhae', 'Tae', 'Aly', 'Nim', 'Ise', 'Ova']
const MID = ['la', 'li', 'ra', 're', 'va', 'ne', 'na', 'ri', 'sse', 'lo', '', '']
const TAIL = ['iel', 'wyn', 'ane', 'eth', 'ara', 'ith', 'elle', 'orin', 'ys', 'ael', 'arë', 'ilwe', 'ondë', 'uin', 'avel', 'issë']

// Names and words from well-known fantasy books and games that a generated name must never contain
// (lower-case, accents removed). Extend it if a generated name ever looks familiar.
const DENY = [
  'gondor', 'rohan', 'mordor', 'shire', 'arnor', 'lorien', 'rivendell', 'imladris', 'isengard', 'moria', 'erebor', 'mirkwood',
  'valinor', 'numenor', 'beleriand', 'eriador', 'harad', 'mithril', 'elrond', 'galadriel', 'aragorn', 'gandalf',
  'sauron', 'saruman', 'frodo', 'bilbo', 'gimli', 'legolas', 'arwen', 'eowyn', 'faramir', 'boromir', 'denethor', 'theoden',
  'ithilien', 'osgiliath', 'minas', 'tirith', 'morgul', 'anduin', 'fangorn', 'hobbit', 'tolkien', 'silmaril', 'eldar',
  'edain', 'dunedain', 'esgaroth', 'edoras', 'umbar', 'angmar', 'thranduil', 'celeborn', 'elendil', 'isildur', 'valar',
  'maiar', 'balrog', 'nazgul', 'smaug', 'gollum', 'sindar', 'noldor', 'quenya', 'sindarin', 'tengwar', 'westeros',
  'winterfell', 'tamriel', 'skyrim', 'azeroth', 'narnia', 'earthsea', 'eregion', 'lindon', 'doriath', 'luthien', 'beren',
  'earendil', 'elwing', 'feanor', 'fingolfin', 'turgon', 'glorfindel', 'celebrimbor', 'haldir', 'nienor', 'melian',
  'thingol', 'idril', 'elessar', 'undomiel', 'nimrodel', 'amroth', 'rauros', 'nimloth', 'telperion', 'laurelin',
  'alqualonde', 'tirion', 'taniquetil', 'elbereth', 'gilthoniel', 'galadhrim', 'mallorn', 'athelas', 'lembas', 'miruvor',
  'mithrandir', 'olorin', 'ancalagon', 'glaurung', 'ungoliant', 'shelob', 'tinuviel', 'eressea', 'avallone', 'hithlum',
  'nargothrond', 'gondolin', 'menegroth', 'ossiriand', 'sirion', 'gelion', 'yavanna', 'varda', 'manwe', 'ulmo', 'nienna',
  'vaire', 'estel', 'ithil', 'anor', 'rhun', 'dale', 'bree', 'arda', 'aman', 'eru', 'ilmarin', 'oiolosse', 'ainur', 'nandor',
  'teleri', 'vanyar', 'aule', 'orome', 'nessa', 'tulkas', 'irmo', 'namo', 'este', 'elenwe', 'nerdanel', 'miriel', 'indis',
  'aredhel', 'finrod', 'galadhon', 'finduilas', 'gwindor', 'nimrais', 'lebennin', 'belfalas', 'ithildin', 'orodruin',
]
function hash(s: string, salt = 0) {
  let h = 2166136261 ^ salt
  for (const ch of s) h = Math.imul(h ^ ch.charCodeAt(0), 16777619)
  return h >>> 0
}

const plain = (s: string) => s.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase()
export const isDenied = (name: string) => DENY.some(d => plain(name).includes(d))

/** Deterministic invented name for a seed; re-rolls if it would collide with a known name. */
export function inventName(seed: string): string {
  for (let salt = 0; salt < 50; salt++) {
    const h = hash(seed, salt)
    const name = HEAD[h % HEAD.length] + MID[(h >>> 5) % MID.length] + TAIL[(h >>> 9) % TAIL.length]
    if (!isDenied(name)) return name
  }
  return 'Sin nombre'
}

/** "Comarca del Norte II" → "Marca del Norte II", "Pueblo de Kino" → "Aldea de Kino". */
export function atlasGloss(title: string): string {
  return title
    .replace(/^Comarca /, 'Marca ')
    .replace(/^Frontera /, 'Confín ')
    .replace(/^Pueblo de /, 'Aldea de ')
    .replace(/^El Corazón/, 'La Ciudadela')
}

/** Sencillo: everyday words for the generated titles. "Comarca del Poniente" → "Poniente",
 *  "Frontera del Sur" → "Afueras del Sur", "El Corazón" → "Centro", "Pueblo de Kino" → "Kino". */
export function plainTitle(title: string): string {
  return title
    .replace(/^Comarca del? /, '')
    .replace(/^Frontera /, 'Afueras ')
    .replace(/^El Corazón/, 'Centro')
    .replace(/^Pueblo de /, '')
}

export interface RealmLabel {
  /** big name on the banner */
  name: string
  /** line under it */
  sub: string
  /** plain words for tooltips and the ficha */
  zone: string
}

/** How a territory is named in each skin. */
export function realmLabel(r: Realm, skin: Skin): RealmLabel {
  const real = shortName(r.name)
  // Sencillo: only the real place name, no invented titles
  if (skin === 'sencillo') {
    const name = real ?? plainTitle(r.title)
    return { name, sub: '', zone: name }
  }
  if (skin === 'norteno') return { name: real ?? r.title, sub: real ? r.title : '', zone: real ?? r.title }
  const gloss = atlasGloss(r.title)
  // towns already carry their real name in the gloss ("Aldea de Bahía de Kino")
  const sub = real && !r.id.startsWith('L') ? `${gloss} · ${real}` : gloss
  return { name: inventName(r.id), sub, zone: real ?? gloss }
}

/** Invented epithet for the whole map, shown with its Spanish meaning. */
export const ATLAS_EPITHET = { name: inventName('juan-jose-rios-valle'), gloss: 'Tierra del Valle Fértil' }
