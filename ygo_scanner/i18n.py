"""Übersetzungen (DE, EN, ES, FR, IT).

Verwendung:  t("key", n=3)  ->  Text in der eingestellten Sprache, Platzhalter per str.format.
Neue Sprache: Code in LANGUAGES ergänzen und in jedem Eintrag von STRINGS übersetzen
(fehlende Übersetzungen fallen automatisch auf Englisch zurück).
"""
LANGUAGES = {"de": "Deutsch", "en": "English", "es": "Español", "fr": "Français", "it": "Italiano"}
_lang = "en"


def set_language(code: str | None) -> str:
    global _lang
    _lang = code if code in LANGUAGES else "en"
    return _lang


def language() -> str:
    return _lang


def system_language() -> str:
    try:
        from PySide6.QtCore import QLocale
        code = QLocale.system().name()[:2]
    except Exception:  # noqa: BLE001
        code = "en"
    return code if code in LANGUAGES else "en"


def t(key: str, **kw) -> str:
    entry = STRINGS.get(key)
    if entry is None:
        return key
    text = entry.get(_lang) or entry.get("en") or key
    return text.format(**kw) if kw else text


STRINGS: dict[str, dict[str, str]] = {
    # ------------------------------------------------------------------ allgemein
    "disclaimer": {
        "de": "{app} ist ein kostenloses Fan-Projekt und steht in keiner Verbindung zu Konami. "
              "Yu-Gi-Oh! ist eine Marke von Konami. Preise ohne Gewähr.",
        "en": "{app} is a free fan project and is not affiliated with Konami. "
              "Yu-Gi-Oh! is a trademark of Konami. Prices without guarantee.",
        "es": "{app} es un proyecto gratuito de fans y no está afiliado a Konami. "
              "Yu-Gi-Oh! es una marca de Konami. Precios sin garantía.",
        "fr": "{app} est un projet de fans gratuit, sans lien avec Konami. "
              "Yu-Gi-Oh! est une marque de Konami. Prix sans garantie.",
        "it": "{app} è un progetto gratuito di fan e non è affiliato a Konami. "
              "Yu-Gi-Oh! è un marchio di Konami. Prezzi senza garanzia.",
    },
    # ------------------------------------------------------------------ Kamera-Thread
    "loading_model": {"de": "Lade Erkennung (KI-Modell) …", "en": "Loading recognition (AI model) …",
                      "es": "Cargando reconocimiento (modelo de IA) …", "fr": "Chargement de la reconnaissance (modèle IA) …",
                      "it": "Caricamento riconoscimento (modello IA) …"},
    "camera_failed": {"de": "Kamera {n} konnte nicht geöffnet werden – andere Kamera in den Einstellungen wählen.",
                      "en": "Camera {n} could not be opened – choose another camera in the settings.",
                      "es": "No se pudo abrir la cámara {n}: elige otra cámara en los ajustes.",
                      "fr": "Impossible d'ouvrir la caméra {n} – choisissez une autre caméra dans les paramètres.",
                      "it": "Impossibile aprire la fotocamera {n} – scegli un'altra fotocamera nelle impostazioni."},
    "ready": {"de": "Bereit – lege eine Karte unter die Kamera", "en": "Ready – place a card under the camera",
              "es": "Listo: coloca una carta bajo la cámara", "fr": "Prêt – placez une carte sous la caméra",
              "it": "Pronto – metti una carta sotto la fotocamera"},
    "no_frame": {"de": "Kein Kamerabild", "en": "No camera image", "es": "Sin imagen de cámara",
                 "fr": "Pas d'image de la caméra", "it": "Nessuna immagine dalla fotocamera"},
    "starting": {"de": "Starte …", "en": "Starting …", "es": "Iniciando …", "fr": "Démarrage …", "it": "Avvio …"},
    # ------------------------------------------------------------------ Werkzeugleiste
    "alarm_from": {"de": "Wert-Alarm ab", "en": "Value alert from", "es": "Alerta de valor desde",
                   "fr": "Alerte valeur dès", "it": "Avviso valore da"},
    "auto_collection": {"de": "Erkannte Karten automatisch in die Sammlung",
                        "en": "Add recognized cards to collection automatically",
                        "es": "Añadir cartas reconocidas a la colección automáticamente",
                        "fr": "Ajouter automatiquement les cartes reconnues à la collection",
                        "it": "Aggiungi automaticamente le carte riconosciute alla collezione"},
    "zoom": {"de": "Vorschau-Zoom", "en": "Preview zoom", "es": "Zoom de vista previa", "fr": "Zoom de l'aperçu",
             "it": "Zoom anteprima"},
    "sharp_none": {"de": "Schärfe: –", "en": "Sharpness: –", "es": "Nitidez: –", "fr": "Netteté : –",
                   "it": "Nitidezza: –"},
    "sharp_nocard": {"de": "Schärfe: keine Karte", "en": "Sharpness: no card", "es": "Nitidez: sin carta",
                     "fr": "Netteté : pas de carte", "it": "Nitidezza: nessuna carta"},
    "sharp_fmt": {"de": "Schärfe: {value}  ·  Bestwert {best}", "en": "Sharpness: {value}  ·  best {best}",
                  "es": "Nitidez: {value}  ·  mejor {best}", "fr": "Netteté : {value}  ·  meilleure {best}",
                  "it": "Nitidezza: {value}  ·  migliore {best}"},
    "sharp_good": {"de": "gut", "en": "good", "es": "buena", "fr": "bonne", "it": "buona"},
    "sharp_ok": {"de": "ok", "en": "ok", "es": "aceptable", "fr": "correcte", "it": "ok"},
    "sharp_blurry": {"de": "unscharf", "en": "blurry", "es": "borrosa", "fr": "floue", "it": "sfocata"},
    "quota_tooltip": {
        "de": "Verbleibende Anfragen an die Live-Preis-API (TCG Price Lookup) heute.\n"
              "Bereits geladene Karten kommen 3 Tage aus dem Speicher und kosten nichts.",
        "en": "Remaining requests to the live price API (TCG Price Lookup) today.\n"
              "Cards already loaded are cached for 3 days and cost nothing.",
        "es": "Consultas restantes hoy a la API de precios en vivo (TCG Price Lookup).\n"
              "Las cartas ya cargadas se guardan 3 días y no cuestan nada.",
        "fr": "Requêtes restantes aujourd'hui vers l'API de prix en direct (TCG Price Lookup).\n"
              "Les cartes déjà chargées sont gardées 3 jours et ne coûtent rien.",
        "it": "Richieste rimanenti oggi all'API dei prezzi live (TCG Price Lookup).\n"
              "Le carte già caricate restano in memoria 3 giorni e non costano nulla.",
    },
    "quota_no_key": {"de": "Live-Preise: kein API-Key", "en": "Live prices: no API key",
                     "es": "Precios en vivo: sin clave API", "fr": "Prix en direct : pas de clé API",
                     "it": "Prezzi live: nessuna chiave API"},
    "quota_unknown": {"de": "Live-Preise: Kontingent noch unbekannt", "en": "Live prices: quota not known yet",
                      "es": "Precios en vivo: cupo aún desconocido", "fr": "Prix en direct : quota encore inconnu",
                      "it": "Prezzi live: quota ancora sconosciuta"},
    "quota_fmt": {"de": "Live-Preise: {rem} / {lim} heute", "en": "Live prices: {rem} / {lim} today",
                  "es": "Precios en vivo: {rem} / {lim} hoy", "fr": "Prix en direct : {rem} / {lim} aujourd'hui",
                  "it": "Prezzi live: {rem} / {lim} oggi"},
    "quota_reset": {"de": "  ·  neu ab {time} Uhr", "en": "  ·  resets at {time}", "es": "  ·  se renueva a las {time}",
                    "fr": "  ·  renouvelé à {time}", "it": "  ·  si rinnova alle {time}"},
    "refresh_btn": {"de": "⟳ Preise aktualisieren", "en": "⟳ Update prices", "es": "⟳ Actualizar precios",
                    "fr": "⟳ Mettre à jour les prix", "it": "⟳ Aggiorna prezzi"},
    "refreshing": {"de": "⟳ aktualisiere …", "en": "⟳ updating …", "es": "⟳ actualizando …",
                   "fr": "⟳ mise à jour …", "it": "⟳ aggiornamento …"},
    "refresh_tooltip": {
        "de": "Lädt die aktuellen Cardmarket-/TCGplayer-Preise aller Karten (ca. 1–2 Minuten).\n"
              "Passiert sonst automatisch einmal am Tag beim Start.",
        "en": "Downloads current Cardmarket/TCGplayer prices for all cards (about 1–2 minutes).\n"
              "Otherwise happens automatically once a day at startup.",
        "es": "Descarga los precios actuales de Cardmarket/TCGplayer de todas las cartas (1–2 minutos).\n"
              "Si no, se hace automáticamente una vez al día al iniciar.",
        "fr": "Télécharge les prix actuels Cardmarket/TCGplayer de toutes les cartes (1 à 2 minutes).\n"
              "Sinon, cela se fait automatiquement une fois par jour au démarrage.",
        "it": "Scarica i prezzi attuali Cardmarket/TCGplayer di tutte le carte (circa 1–2 minuti).\n"
              "Altrimenti avviene automaticamente una volta al giorno all'avvio.",
    },
    "export_btn": {"de": "Scan-Liste als CSV", "en": "Export scan list (CSV)", "es": "Exportar lista (CSV)",
                   "fr": "Exporter la liste (CSV)", "it": "Esporta lista (CSV)"},
    "settings_btn": {"de": "⚙ Einstellungen", "en": "⚙ Settings", "es": "⚙ Ajustes", "fr": "⚙ Paramètres",
                     "it": "⚙ Impostazioni"},
    # ------------------------------------------------------------------ Ergebnis-Karte
    "no_card_yet": {"de": "Noch keine Karte", "en": "No card yet", "es": "Aún no hay carta",
                    "fr": "Pas encore de carte", "it": "Ancora nessuna carta"},
    "condition": {"de": "Zustand:", "en": "Condition:", "es": "Estado:", "fr": "État :", "it": "Condizione:"},
    "live_btn": {"de": "Live-Preise laden  [L]", "en": "Load live prices  [L]", "es": "Cargar precios en vivo  [L]",
                 "fr": "Charger les prix en direct  [L]", "it": "Carica prezzi live  [L]"},
    "accept_btn": {"de": "Übernehmen  [Leer]", "en": "Accept  [Space]", "es": "Aceptar  [Espacio]",
                   "fr": "Valider  [Espace]", "it": "Conferma  [Spazio]"},
    "collect_btn": {"de": "Zur Sammlung  [S]", "en": "Add to collection  [S]", "es": "A la colección  [S]",
                    "fr": "À la collection  [S]", "it": "Alla collezione  [S]"},
    "rescan_btn": {"de": "Neu scannen  [R]", "en": "Rescan  [R]", "es": "Reescanear  [R]", "fr": "Rescanner  [R]",
                   "it": "Riscansiona  [R]"},
    "confidence": {"de": "Sicherheit", "en": "Confidence", "es": "Confianza", "fr": "Confiance", "it": "Affidabilità"},
    "uncertain": {"de": "unsicher", "en": "uncertain", "es": "dudoso", "fr": "incertain", "it": "incerto"},
    "cm_from": {"de": "Cardmarket ab", "en": "Cardmarket from", "es": "Cardmarket desde", "fr": "Cardmarket dès",
                "it": "Cardmarket da"},
    "tcg_from": {"de": "TCGplayer ab", "en": "TCGplayer from", "es": "TCGplayer desde", "fr": "TCGplayer dès",
                 "it": "TCGplayer da"},
    "no_price_known": {"de": "kein Preis bekannt", "en": "no price known", "es": "sin precio conocido",
                       "fr": "aucun prix connu", "it": "nessun prezzo noto"},
    "no_price": {"de": "kein Preis", "en": "no price", "es": "sin precio", "fr": "pas de prix", "it": "nessun prezzo"},
    "in_collection_n": {"de": "In deiner Sammlung: {n}×", "en": "In your collection: {n}×",
                        "es": "En tu colección: {n}×", "fr": "Dans ta collection : {n}×",
                        "it": "Nella tua collezione: {n}×"},
    "not_in_collection": {"de": "Noch nicht in deiner Sammlung", "en": "Not in your collection yet",
                          "es": "Aún no está en tu colección", "fr": "Pas encore dans ta collection",
                          "it": "Non ancora nella tua collezione"},
    "alarm_text": {"de": "★ WERTVOLL – über {value}!", "en": "★ VALUABLE – over {value}!",
                   "es": "★ VALIOSA – más de {value}!", "fr": "★ PRÉCIEUSE – plus de {value} !",
                   "it": "★ PREZIOSA – oltre {value}!"},
    "rarity_title_live": {
        "de": "Seltenheit wählen – <b>Live-Preise</b> TCGplayer, Zustand {cond} (günstigster Druck):",
        "en": "Choose rarity – <b>live prices</b> TCGplayer, condition {cond} (cheapest printing):",
        "es": "Elige rareza – <b>precios en vivo</b> TCGplayer, estado {cond} (impresión más barata):",
        "fr": "Choisir la rareté – <b>prix en direct</b> TCGplayer, état {cond} (impression la moins chère) :",
        "it": "Scegli rarità – <b>prezzi live</b> TCGplayer, condizione {cond} (stampa più economica):",
    },
    "rarity_title_daily": {
        "de": "Seltenheit wählen – TCGplayer-Tagespreise (günstigster Druck)  ·  Zustand anklicken lädt Live-Preise",
        "en": "Choose rarity – TCGplayer daily prices (cheapest printing)  ·  click a condition for live prices",
        "es": "Elige rareza – precios diarios de TCGplayer (impresión más barata)  ·  pulsa un estado para precios en vivo",
        "fr": "Choisir la rareté – prix du jour TCGplayer (impression la moins chère)  ·  cliquer un état charge les prix en direct",
        "it": "Scegli rarità – prezzi giornalieri TCGplayer (stampa più economica)  ·  clicca una condizione per i prezzi live",
    },
    "rarity_title_ygo": {
        "de": "Seltenheit wählen (YGOPRODeck-Preise, oft lückenhaft/veraltet)",
        "en": "Choose rarity (YGOPRODeck prices, often incomplete/outdated)",
        "es": "Elige rareza (precios de YGOPRODeck, a menudo incompletos/antiguos)",
        "fr": "Choisir la rareté (prix YGOPRODeck, souvent incomplets/anciens)",
        "it": "Scegli rarità (prezzi YGOPRODeck, spesso incompleti/vecchi)",
    },
    "rarity_hint_live": {"de": "  ·  [L] lädt aktuelle Preise", "en": "  ·  [L] loads current prices",
                         "es": "  ·  [L] carga precios actuales", "fr": "  ·  [L] charge les prix actuels",
                         "it": "  ·  [L] carica i prezzi attuali"},
    "no_rarities": {"de": "Keine Seltenheiten bekannt", "en": "No rarities known", "es": "No se conocen rarezas",
                    "fr": "Aucune rareté connue", "it": "Nessuna rarità nota"},
    "cond_tooltip": {"de": "Lädt Live-Preise für diesen Zustand (1 Anfrage)",
                     "en": "Loads live prices for this condition (1 request)",
                     "es": "Carga precios en vivo para este estado (1 consulta)",
                     "fr": "Charge les prix en direct pour cet état (1 requête)",
                     "it": "Carica i prezzi live per questa condizione (1 richiesta)"},
    "badge_live": {"de": "● LIVE-Preise", "en": "● LIVE prices", "es": "● Precios EN VIVO", "fr": "● Prix EN DIRECT",
                   "it": "● Prezzi LIVE"},
    "badge_daily": {"de": "● TCGplayer-Tagespreise · Stand {date}", "en": "● TCGplayer daily prices · as of {date}",
                    "es": "● Precios diarios TCGplayer · {date}", "fr": "● Prix du jour TCGplayer · {date}",
                    "it": "● Prezzi giornalieri TCGplayer · {date}"},
    "badge_loading": {"de": "● lade Live-Preise …", "en": "● loading live prices …", "es": "● cargando precios …",
                      "fr": "● chargement des prix …", "it": "● caricamento prezzi …"},
    "badge_ygo": {"de": "● OFFLINE-Preise (evtl. veraltet)", "en": "● OFFLINE prices (may be outdated)",
                  "es": "● Precios OFFLINE (pueden estar desactualizados)",
                  "fr": "● Prix HORS LIGNE (peut-être anciens)", "it": "● Prezzi OFFLINE (forse non aggiornati)"},
    "badge_ygo_L": {"de": "  ·  [L] für Live", "en": "  ·  [L] for live", "es": "  ·  [L] en vivo",
                    "fr": "  ·  [L] en direct", "it": "  ·  [L] per live"},
    # ------------------------------------------------------------------ Tabellen
    "tab_scan": {"de": "Scan-Liste", "en": "Scan list", "es": "Lista de escaneo", "fr": "Liste de scan",
                 "it": "Lista scansioni"},
    "tab_coll": {"de": "Sammlung", "en": "Collection", "es": "Colección", "fr": "Collection", "it": "Collezione"},
    "col_card": {"de": "Karte", "en": "Card", "es": "Carta", "fr": "Carte", "it": "Carta"},
    "col_rarity": {"de": "Seltenheit", "en": "Rarity", "es": "Rareza", "fr": "Rareté", "it": "Rarità"},
    "col_count": {"de": "Anzahl", "en": "Qty", "es": "Cant.", "fr": "Qté", "it": "Qtà"},
    "col_value": {"de": "Wert (CM)", "en": "Value (CM)", "es": "Valor (CM)", "fr": "Valeur (CM)", "it": "Valore (CM)"},
    "click_opens": {"de": "Klicken öffnet die Seite", "en": "Click to open the page", "es": "Clic para abrir la página",
                    "fr": "Cliquer pour ouvrir la page", "it": "Clicca per aprire la pagina"},
    "scan_total": {"de": "{n} Karten  ·  Summe Cardmarket {cm}  ·  TCGplayer {tcg}",
                   "en": "{n} cards  ·  total Cardmarket {cm}  ·  TCGplayer {tcg}",
                   "es": "{n} cartas  ·  total Cardmarket {cm}  ·  TCGplayer {tcg}",
                   "fr": "{n} cartes  ·  total Cardmarket {cm}  ·  TCGplayer {tcg}",
                   "it": "{n} carte  ·  totale Cardmarket {cm}  ·  TCGplayer {tcg}"},
    "coll_total": {"de": "{n} Karten ({k} verschiedene)  ·  Wert ca. {value} (Cardmarket)",
                   "en": "{n} cards ({k} different)  ·  value approx. {value} (Cardmarket)",
                   "es": "{n} cartas ({k} distintas)  ·  valor aprox. {value} (Cardmarket)",
                   "fr": "{n} cartes ({k} différentes)  ·  valeur env. {value} (Cardmarket)",
                   "it": "{n} carte ({k} diverse)  ·  valore circa {value} (Cardmarket)"},
    "hint_keys": {
        "de": "1/2/3 wählen · Leer übernehmen · S Sammlung · R neu · L Live-Preise · Strg+Z rückgängig · "
              "Entf entfernt aus Sammlung · Preise anklicken öffnet die Seite",
        "en": "1/2/3 choose · Space accept · S collection · R rescan · L live prices · Ctrl+Z undo · "
              "Del removes from collection · click prices to open the page",
        "es": "1/2/3 elegir · Espacio aceptar · S colección · R reescanear · L precios en vivo · Ctrl+Z deshacer · "
              "Supr quita de la colección · clic en precios abre la página",
        "fr": "1/2/3 choisir · Espace valider · S collection · R rescanner · L prix en direct · Ctrl+Z annuler · "
              "Suppr retire de la collection · cliquer un prix ouvre la page",
        "it": "1/2/3 scegli · Spazio conferma · S collezione · R riscansiona · L prezzi live · Ctrl+Z annulla · "
              "Canc rimuove dalla collezione · clic sui prezzi apre la pagina",
    },
    # ------------------------------------------------------------------ Statusmeldungen
    "status_uncertain": {"de": "Unsicher – bitte mit 1/2/3 die richtige Karte wählen",
                         "en": "Uncertain – please choose the right card with 1/2/3",
                         "es": "Dudoso: elige la carta correcta con 1/2/3",
                         "fr": "Incertain – choisissez la bonne carte avec 1/2/3",
                         "it": "Incerto – scegli la carta giusta con 1/2/3"},
    "status_recognized": {"de": "Erkannt: {name}", "en": "Recognized: {name}", "es": "Reconocida: {name}",
                          "fr": "Reconnue : {name}", "it": "Riconosciuta: {name}"},
    "status_accepted": {"de": "Übernommen: {name}", "en": "Accepted: {name}", "es": "Aceptada: {name}",
                        "fr": "Validée : {name}", "it": "Confermata: {name}"},
    "status_added": {"de": "Zur Sammlung hinzugefügt: {name} (jetzt {n}×)",
                     "en": "Added to collection: {name} (now {n}×)",
                     "es": "Añadida a la colección: {name} (ahora {n}×)",
                     "fr": "Ajoutée à la collection : {name} (maintenant {n}×)",
                     "it": "Aggiunta alla collezione: {name} (ora {n}×)"},
    "status_select_remove": {"de": "Zum Entfernen erst eine Karte im Tab 'Sammlung' anklicken",
                             "en": "To remove, first click a card in the 'Collection' tab",
                             "es": "Para quitar, primero haz clic en una carta de la pestaña 'Colección'",
                             "fr": "Pour retirer, cliquez d'abord une carte dans l'onglet « Collection »",
                             "it": "Per rimuovere, clicca prima una carta nella scheda 'Collezione'"},
    "status_removed_one": {"de": "Ein Exemplar aus der Sammlung entfernt", "en": "Removed one copy from the collection",
                           "es": "Se quitó una copia de la colección", "fr": "Un exemplaire retiré de la collection",
                           "it": "Rimossa una copia dalla collezione"},
    "status_rescanning": {"de": "Scanne neu …", "en": "Rescanning …", "es": "Reescaneando …", "fr": "Nouveau scan …",
                          "it": "Nuova scansione …"},
    "status_removed_list": {"de": "Aus Scan-Liste entfernt: {name}", "en": "Removed from scan list: {name}",
                            "es": "Quitada de la lista: {name}", "fr": "Retirée de la liste : {name}",
                            "it": "Rimossa dalla lista: {name}"},
    "status_list_empty": {"de": "Scan-Liste ist leer", "en": "Scan list is empty", "es": "La lista está vacía",
                          "fr": "La liste est vide", "it": "La lista è vuota"},
    "status_saved": {"de": "Gespeichert: {path}", "en": "Saved: {path}", "es": "Guardado: {path}",
                     "fr": "Enregistré : {path}", "it": "Salvato: {path}"},
    "status_rarity": {"de": "Seltenheit: {r}", "en": "Rarity: {r}", "es": "Rareza: {r}", "fr": "Rareté : {r}",
                      "it": "Rarità: {r}"},
    "status_rarity_cleared": {"de": "Seltenheit abgewählt", "en": "Rarity cleared", "es": "Rareza quitada",
                              "fr": "Rareté désélectionnée", "it": "Rarità deselezionata"},
    "status_no_key": {"de": "Kein API-Key für Live-Preise – in den Einstellungen eintragen",
                      "en": "No API key for live prices – enter one in the settings",
                      "es": "Sin clave API para precios en vivo: introdúcela en los ajustes",
                      "fr": "Pas de clé API pour les prix en direct – saisissez-la dans les paramètres",
                      "it": "Nessuna chiave API per i prezzi live – inseriscila nelle impostazioni"},
    "status_loading_live": {"de": "Lade Live-Preise für {name} …", "en": "Loading live prices for {name} …",
                            "es": "Cargando precios en vivo de {name} …", "fr": "Chargement des prix de {name} …",
                            "it": "Caricamento prezzi live di {name} …"},
    "status_live_loaded": {"de": "Live-Preise geladen: {n} Drucke", "en": "Live prices loaded: {n} printings",
                           "es": "Precios cargados: {n} impresiones", "fr": "Prix chargés : {n} impressions",
                           "it": "Prezzi caricati: {n} stampe"},
    "status_requests_left": {"de": "  ·  noch {n} Anfragen heute", "en": "  ·  {n} requests left today",
                             "es": "  ·  quedan {n} consultas hoy", "fr": "  ·  encore {n} requêtes aujourd'hui",
                             "it": "  ·  ancora {n} richieste oggi"},
    "status_live_failed": {"de": "Live-Preise für {name} nicht verfügbar: {msg}",
                           "en": "Live prices for {name} not available: {msg}",
                           "es": "Precios en vivo de {name} no disponibles: {msg}",
                           "fr": "Prix en direct de {name} indisponibles : {msg}",
                           "it": "Prezzi live di {name} non disponibili: {msg}"},
    "status_settings_saved": {"de": "Einstellungen gespeichert", "en": "Settings saved", "es": "Ajustes guardados",
                              "fr": "Paramètres enregistrés", "it": "Impostazioni salvate"},
    "status_switch_camera": {"de": "Wechsle Kamera …", "en": "Switching camera …", "es": "Cambiando de cámara …",
                             "fr": "Changement de caméra …", "it": "Cambio fotocamera …"},
    "status_updating_prices": {"de": "Aktualisiere Preise …", "en": "Updating prices …",
                               "es": "Actualizando precios …", "fr": "Mise à jour des prix …",
                               "it": "Aggiornamento prezzi …"},
    "status_prices_progress": {"de": "Aktualisiere Tagespreise: {done}/{total} Sets",
                               "en": "Updating daily prices: {done}/{total} sets",
                               "es": "Actualizando precios diarios: {done}/{total} sets",
                               "fr": "Mise à jour des prix du jour : {done}/{total} sets",
                               "it": "Aggiornamento prezzi giornalieri: {done}/{total} set"},
    "status_prices_updated": {"de": "Preise aktualisiert (Stand {date})", "en": "Prices updated (as of {date})",
                              "es": "Precios actualizados ({date})", "fr": "Prix mis à jour ({date})",
                              "it": "Prezzi aggiornati ({date})"},
    "status_prices_failed": {"de": "Preise konnten nicht aktualisiert werden: {msg}",
                             "en": "Prices could not be updated: {msg}",
                             "es": "No se pudieron actualizar los precios: {msg}",
                             "fr": "Impossible de mettre à jour les prix : {msg}",
                             "it": "Impossibile aggiornare i prezzi: {msg}"},
    "err_no_key": {"de": "kein API-Key", "en": "no API key", "es": "sin clave API", "fr": "pas de clé API",
                   "it": "nessuna chiave API"},
    "err_connection": {"de": "keine Verbindung", "en": "no connection", "es": "sin conexión", "fr": "pas de connexion",
                       "it": "nessuna connessione"},
    "err_limit": {"de": "Tageslimit erreicht", "en": "daily limit reached", "es": "límite diario alcanzado",
                  "fr": "limite quotidienne atteinte", "it": "limite giornaliero raggiunto"},
    "err_http": {"de": "Fehler der Preis-API", "en": "price API error", "es": "error de la API de precios",
                 "fr": "erreur de l'API de prix", "it": "errore dell'API prezzi"},
    # ------------------------------------------------------------------ CSV
    "csv_header": {"de": "Name;Typ;Seltenheit;Cardmarket (EUR, ab);TCGplayer (USD);Sicherheit",
                   "en": "Name;Type;Rarity;Cardmarket (EUR, from);TCGplayer (USD);Confidence",
                   "es": "Nombre;Tipo;Rareza;Cardmarket (EUR, desde);TCGplayer (USD);Confianza",
                   "fr": "Nom;Type;Rareté;Cardmarket (EUR, dès);TCGplayer (USD);Confiance",
                   "it": "Nome;Tipo;Rarità;Cardmarket (EUR, da);TCGplayer (USD);Affidabilità"},
    # ------------------------------------------------------------------ Einstellungen
    "settings_title": {"de": "Einstellungen", "en": "Settings", "es": "Ajustes", "fr": "Paramètres",
                       "it": "Impostazioni"},
    "camera": {"de": "Kamera", "en": "Camera", "es": "Cámara", "fr": "Caméra", "it": "Fotocamera"},
    "camera_n": {"de": "Kamera {n}", "en": "Camera {n}", "es": "Cámara {n}", "fr": "Caméra {n}",
                 "it": "Fotocamera {n}"},
    "language": {"de": "Sprache", "en": "Language", "es": "Idioma", "fr": "Langue", "it": "Lingua"},
    "language_restart": {"de": "Die Sprache wird nach einem Neustart der App übernommen.",
                         "en": "The language is applied after restarting the app.",
                         "es": "El idioma se aplica tras reiniciar la aplicación.",
                         "fr": "La langue s'applique après le redémarrage de l'application.",
                         "it": "La lingua viene applicata dopo il riavvio dell'app."},
    "api_key": {"de": "TCG Price Lookup\nAPI-Key", "en": "TCG Price Lookup\nAPI key", "es": "TCG Price Lookup\nclave API",
                "fr": "TCG Price Lookup\nclé API", "it": "TCG Price Lookup\nchiave API"},
    "api_key_placeholder": {"de": "optional – für Live-Preise nach Zustand",
                            "en": "optional – for live prices by condition",
                            "es": "opcional: para precios en vivo por estado",
                            "fr": "facultatif – pour les prix en direct par état",
                            "it": "facoltativa – per i prezzi live per condizione"},
    "show": {"de": "anzeigen", "en": "show", "es": "mostrar", "fr": "afficher", "it": "mostra"},
    "api_help": {
        "de": "<b>So bekommst du einen kostenlosen Key:</b><br>"
              "1. Öffne <a style='color:#74c0fc' href='https://tcgpricelookup.com/tcg-api'>tcgpricelookup.com/tcg-api</a><br>"
              "2. Kostenlos registrieren (Free-Plan, ca. 100 Anfragen pro Tag)<br>"
              "3. Im Dashboard den API-Key kopieren und hier einfügen<br>"
              "<i>Ohne Key funktioniert alles außer den Preisen nach Zustand (NM/LP/…).</i>",
        "en": "<b>How to get a free key:</b><br>"
              "1. Open <a style='color:#74c0fc' href='https://tcgpricelookup.com/tcg-api'>tcgpricelookup.com/tcg-api</a><br>"
              "2. Sign up for free (free plan, about 100 requests per day)<br>"
              "3. Copy the API key from your dashboard and paste it here<br>"
              "<i>Without a key everything works except prices by condition (NM/LP/…).</i>",
        "es": "<b>Cómo conseguir una clave gratis:</b><br>"
              "1. Abre <a style='color:#74c0fc' href='https://tcgpricelookup.com/tcg-api'>tcgpricelookup.com/tcg-api</a><br>"
              "2. Regístrate gratis (plan gratuito, unas 100 consultas al día)<br>"
              "3. Copia la clave API de tu panel y pégala aquí<br>"
              "<i>Sin clave todo funciona salvo los precios por estado (NM/LP/…).</i>",
        "fr": "<b>Obtenir une clé gratuite :</b><br>"
              "1. Ouvrez <a style='color:#74c0fc' href='https://tcgpricelookup.com/tcg-api'>tcgpricelookup.com/tcg-api</a><br>"
              "2. Inscrivez-vous gratuitement (offre gratuite, environ 100 requêtes par jour)<br>"
              "3. Copiez la clé API depuis votre tableau de bord et collez-la ici<br>"
              "<i>Sans clé, tout fonctionne sauf les prix par état (NM/LP/…).</i>",
        "it": "<b>Come ottenere una chiave gratuita:</b><br>"
              "1. Apri <a style='color:#74c0fc' href='https://tcgpricelookup.com/tcg-api'>tcgpricelookup.com/tcg-api</a><br>"
              "2. Registrati gratis (piano gratuito, circa 100 richieste al giorno)<br>"
              "3. Copia la chiave API dalla dashboard e incollala qui<br>"
              "<i>Senza chiave funziona tutto tranne i prezzi per condizione (NM/LP/…).</i>",
    },
    "live_min": {"de": "Live-Preise automatisch ab", "en": "Load live prices automatically from",
                 "es": "Precios en vivo automáticos desde", "fr": "Prix en direct automatiques dès",
                 "it": "Prezzi live automatici da"},
    "card_db": {"de": "Kartendatenbank", "en": "Card database", "es": "Base de datos de cartas",
                "fr": "Base de cartes", "it": "Database carte"},
    "update_db_btn": {"de": "Neue Karten & Bilder herunterladen", "en": "Download new cards & images",
                      "es": "Descargar cartas e imágenes nuevas", "fr": "Télécharger nouvelles cartes et images",
                      "it": "Scarica nuove carte e immagini"},
    "update_db_hint": {"de": "Lädt nur fehlende Karten nach (z.B. nach einem neuen Set) – meist wenige Minuten.",
                       "en": "Only downloads missing cards (e.g. after a new set) – usually a few minutes.",
                       "es": "Solo descarga las cartas que faltan (p. ej. tras un set nuevo); suele tardar pocos minutos.",
                       "fr": "Ne télécharge que les cartes manquantes (ex. nouveau set) – en général quelques minutes.",
                       "it": "Scarica solo le carte mancanti (es. dopo un nuovo set) – di solito pochi minuti."},
    "save": {"de": "Speichern", "en": "Save", "es": "Guardar", "fr": "Enregistrer", "it": "Salva"},
    "cancel": {"de": "Abbrechen", "en": "Cancel", "es": "Cancelar", "fr": "Annuler", "it": "Annulla"},
    "close": {"de": "Schließen", "en": "Close", "es": "Cerrar", "fr": "Fermer", "it": "Chiudi"},
    # ------------------------------------------------------------------ Einrichtung / Download
    "setup_title": {"de": "Einrichtung", "en": "Setup", "es": "Configuración", "fr": "Installation",
                    "it": "Configurazione"},
    "setup_welcome": {"de": "Willkommen bei {app}!", "en": "Welcome to {app}!", "es": "¡Bienvenido a {app}!",
                      "fr": "Bienvenue dans {app} !", "it": "Benvenuto in {app}!"},
    "setup_intro": {
        "de": "Damit der Scanner Karten erkennen kann, lädt er einmalig alle Kartendaten und Kartenbilder "
              "herunter und bereitet die Erkennung vor:<br><br>"
              "• ca. <b>15.000 Kartenbilder</b> (ca. 500 MB)<br>"
              "• Erkennungs-Index und KI-Modell (läuft lokal auf deinem PC)<br>"
              "• aktuelle Preise<br><br>"
              "Das dauert beim ersten Mal ca. <b>30–40 Minuten</b> und braucht eine Internetverbindung. "
              "Du kannst abbrechen und später weitermachen – Fertiges bleibt erhalten.",
        "en": "To recognize cards, the scanner downloads all card data and card images once and prepares "
              "the recognition:<br><br>"
              "• about <b>15,000 card images</b> (about 500 MB)<br>"
              "• recognition index and AI model (runs locally on your PC)<br>"
              "• current prices<br><br>"
              "The first time this takes about <b>30–40 minutes</b> and needs an internet connection. "
              "You can cancel and continue later – finished parts are kept.",
        "es": "Para reconocer cartas, el escáner descarga una vez todos los datos e imágenes de cartas y prepara "
              "el reconocimiento:<br><br>"
              "• unas <b>15.000 imágenes de cartas</b> (unos 500 MB)<br>"
              "• índice de reconocimiento y modelo de IA (se ejecuta en tu PC)<br>"
              "• precios actuales<br><br>"
              "La primera vez tarda unos <b>30–40 minutos</b> y necesita conexión a internet. "
              "Puedes cancelar y seguir más tarde: lo terminado se conserva.",
        "fr": "Pour reconnaître les cartes, le scanner télécharge une seule fois toutes les données et images "
              "des cartes et prépare la reconnaissance :<br><br>"
              "• environ <b>15 000 images de cartes</b> (environ 500 Mo)<br>"
              "• index de reconnaissance et modèle IA (fonctionne en local sur votre PC)<br>"
              "• prix actuels<br><br>"
              "La première fois, cela prend environ <b>30 à 40 minutes</b> et nécessite Internet. "
              "Vous pouvez annuler et reprendre plus tard – ce qui est fait est conservé.",
        "it": "Per riconoscere le carte, lo scanner scarica una sola volta tutti i dati e le immagini delle carte "
              "e prepara il riconoscimento:<br><br>"
              "• circa <b>15.000 immagini di carte</b> (circa 500 MB)<br>"
              "• indice di riconoscimento e modello IA (gira in locale sul tuo PC)<br>"
              "• prezzi attuali<br><br>"
              "La prima volta richiede circa <b>30–40 minuti</b> e una connessione a internet. "
              "Puoi annullare e continuare più tardi: ciò che è finito resta salvato.",
    },
    "setup_update_intro": {
        "de": "Lädt neue Karten und deren Bilder nach und aktualisiert Erkennung und Preise.",
        "en": "Downloads new cards and their images and updates recognition and prices.",
        "es": "Descarga cartas nuevas y sus imágenes y actualiza el reconocimiento y los precios.",
        "fr": "Télécharge les nouvelles cartes et leurs images et met à jour la reconnaissance et les prix.",
        "it": "Scarica le nuove carte e le loro immagini e aggiorna riconoscimento e prezzi.",
    },
    "setup_start": {"de": "Herunterladen starten", "en": "Start download", "es": "Iniciar descarga",
                    "fr": "Démarrer le téléchargement", "it": "Avvia download"},
    "setup_open_app": {"de": "Scanner starten", "en": "Start scanner", "es": "Iniciar escáner",
                       "fr": "Lancer le scanner", "it": "Avvia scanner"},
    "stage_cards": {"de": "Kartendaten laden", "en": "Downloading card data", "es": "Descargando datos de cartas",
                    "fr": "Téléchargement des données", "it": "Download dati delle carte"},
    "stage_art": {"de": "Kartenbilder herunterladen", "en": "Downloading card images",
                  "es": "Descargando imágenes de cartas", "fr": "Téléchargement des images", "it": "Download immagini"},
    "stage_index": {"de": "Bild-Fingerabdrücke berechnen", "en": "Computing image fingerprints",
                    "es": "Calculando huellas de imagen", "fr": "Calcul des empreintes d'image",
                    "it": "Calcolo impronte immagine"},
    "stage_ai": {"de": "KI-Erkennung vorbereiten", "en": "Preparing AI recognition", "es": "Preparando reconocimiento IA",
                 "fr": "Préparation de la reconnaissance IA", "it": "Preparazione riconoscimento IA"},
    "stage_prices": {"de": "Preise laden", "en": "Downloading prices", "es": "Descargando precios",
                     "fr": "Téléchargement des prix", "it": "Download prezzi"},
    "stage_progress": {"de": "Schritt {step}/{steps}: {stage}  ({done}/{total})",
                       "en": "Step {step}/{steps}: {stage}  ({done}/{total})",
                       "es": "Paso {step}/{steps}: {stage}  ({done}/{total})",
                       "fr": "Étape {step}/{steps} : {stage}  ({done}/{total})",
                       "it": "Passo {step}/{steps}: {stage}  ({done}/{total})"},
    "eta": {"de": "noch ca. {min} min", "en": "about {min} min left", "es": "quedan unos {min} min",
            "fr": "encore environ {min} min", "it": "ancora circa {min} min"},
    "setup_done": {"de": "Fertig! Der Scanner ist einsatzbereit.", "en": "Done! The scanner is ready.",
                   "es": "¡Listo! El escáner está preparado.", "fr": "Terminé ! Le scanner est prêt.",
                   "it": "Fatto! Lo scanner è pronto."},
    "setup_cancelled": {"de": "Abgebrochen – beim nächsten Mal geht es an dieser Stelle weiter.",
                        "en": "Cancelled – next time it continues from here.",
                        "es": "Cancelado: la próxima vez continuará desde aquí.",
                        "fr": "Annulé – la prochaine fois, cela reprendra ici.",
                        "it": "Annullato – la prossima volta riprenderà da qui."},
    "setup_failed": {"de": "Fehler: {msg}<br>Bitte Internetverbindung prüfen und erneut versuchen.",
                     "en": "Error: {msg}<br>Please check your internet connection and try again.",
                     "es": "Error: {msg}<br>Comprueba tu conexión a internet e inténtalo de nuevo.",
                     "fr": "Erreur : {msg}<br>Vérifiez votre connexion Internet et réessayez.",
                     "it": "Errore: {msg}<br>Controlla la connessione a internet e riprova."},
    "setup_cancelling": {"de": "Breche ab …", "en": "Cancelling …", "es": "Cancelando …", "fr": "Annulation …",
                         "it": "Annullamento …"},
}
