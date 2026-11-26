// Map interactions sent to Google Tag Manager's dataLayer (container GTM-P3XKB934, loaded in index.html).
// In GTM, use a "Custom Event" trigger with these event names and Data Layer Variables for the fields.
type Ev =
  | { event: 'cambio_modo'; modo: string }
  | { event: 'abrir_barrio'; barrio: string; territorio: string }
  | { event: 'ver_ficha_punto'; tipo: 'animal' | 'negocio' | 'pozo'; grupo: string }
  | { event: 'cambio_estilo'; estilo: string }

export function track(e: Ev) {
  const w = window as unknown as { dataLayer?: unknown[] }
  ;(w.dataLayer ??= []).push(e)
}
