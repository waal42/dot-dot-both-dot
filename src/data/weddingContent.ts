// src/data/weddingContent.ts
import type { ImageMetadata } from "astro";

// Import all gallery images (Astro processes and compresses these automatically at build time)
import imgLublan from "../assets/lublan.jpg";
import imgSifrovacka from "../assets/sifrovacka.jpg";
import imgVytah2 from "../assets/vytah2.jpg";
import imgSaline from "../assets/salina.jpg";
import imgPlac from "../assets/plac.jpg";
import imgMyvali from "../assets/myvali.jpg";
import imgFabar from "../assets/fabar.jpg";
import imgVytah from "../assets/vytah.jpg";
import imgStehovani from "../assets/stehovani.jpg";
import imgSvetry from "../assets/svetry.jpg";
import imgTmou from "../assets/tmou.jpg";
import imgViden from "../assets/viden.jpg";
import imgParek from "../assets/parek.jpg";
import imgWuppertal from "../assets/wuppertal.jpg";
import imgMore from "../assets/more.jpg";
import imgCap from "../assets/cap.jpg";
import imgSbeerka from "../assets/sbeerka.jpg";
import imgKokorinsko from "../assets/kokorinsko.jpg";
import imgKokorinsko2 from "../assets/kokorinsko2.jpg";

/**
 * Represents a picture in the PhotoSwipe grid gallery.
 */
export interface GalleryImage {
  src: ImageMetadata;
  alt: string;
  /** Size affects the tile aspect ratio in the grid (dense mosaic layout) */
  size: "small" | "large" | "vertical" | "horizontal";
  type?: "image";
}

/**
 * Represents a text-only card in the grid gallery (e.g. quotes, mottos).
 */
export interface GalleryText {
  src: null;
  alt: string;
  type: "text";
  title: string;
  detail: string;
  size: "small" | "large" | "vertical" | "horizontal";
}

export type GalleryItem = GalleryImage | GalleryText;

/**
 * An item in the vertical dot-and-dash wedding day timeline.
 */
export interface ScheduleItem {
  time: string;
  title: string;
  description: string;
}

/**
 * Transportation routing details displayed in the tabs of the venue map section.
 */
export interface TransportOption {
  id: string;
  /** Label on the selector tab */
  label: string;
  icon: "car" | "train" | "bus";
  /** Morse code subtitle decorations */
  morse: string;
  title: string;
  /** Rich text detail of the transport method */
  detail: string;
  marker: {
    /** [Latitude, Longitude] coordinates for Leaflet marker pin */
    coords: [number, number];
    title: string;
    icon: "parking" | "train" | "bus";
  };
}

/**
 * Option inside checkable radio/checkbox/select controls of the RSVP.
 */
export interface FormFieldOption {
  value: string;
  label: string;
  checked: boolean;
}

/**
 * Represents a single input control of the RSVP form.
 */
export interface FormField {
  id: string;
  name: string;
  label: string;
  type: "text" | "email" | "radio" | "select" | "checkbox";
  required: boolean;
  placeholder: string | null;
  /** Optional inner label specific to checkbox items */
  text?: string;
  /** Optional selector ID representing fields which conditionally trigger this input's visibility */
  condition: string | null;
  conditionValue?: string | null;
  options?: FormFieldOption[];
}

/**
 * Structural group dividing RSVP fields.
 */
export interface FormSection {
  section: string;
  grid?: boolean;
  divider?: boolean;
  fields: FormField[];
}

/**
 * Unified data schema holding the entire page content.
 * Edit values below to instantly update the text across the website.
 */
export interface WeddingContent {
  /** Title shown in browser tabs */
  metaTitle: string;
  /** Search engine description of your site */
  metaDescription: string;
  
  /** Hero section shown immediately on page load */
  hero: {
    title: string;
    subtitle: string;
    buttonText: string;
  };
  
  /** Narrative description of the couple and Morse theme explanations */
  aboutUs: {
    title: string;
    motto: string;
    /** Paragraph cards displayed in a two-column grid on desktop */
    sections: {
      id: string;
      title: string;
      /** List of paragraph texts. Supports HTML styling like `<span class="font-bold">` */
      content: string[];
    }[];
    /** Gallery items comprising photos and typographic quote cards */
    gallery: GalleryItem[];
  };
  
  /** Venue, scheduling maps, and transportation selections */
  whenWhere: {
    title: string;
    venueName: string;
    address: string;
    /** [Latitude, Longitude] coordinates for primary wedding location */
    coords: [number, number];
    googleMapsUrl: string;
    /** Short friendly description of why this venue was chosen */
    description: string;
    transportOptions: TransportOption[];
  };
  
  /** Timeline schedule list of the day */
  schedule: {
    title: string;
    items: ScheduleItem[];
  };
  
  /** Wedding gift contributions registry and payment configurations */
  gifts: {
    title: string;
    heading: string;
    description: string;
    accountLabel: string;
    /** Account formatted as "prefix-account / bank" (e.g. 670100-2223828816 / 6210) for SPAYD parsing */
    accountNumber: string;
    accountNote: string;
    qrLabel: string;
    /** Message encoded in the QR payment, uppercase and no accents for compliance (e.g., DAR SVATEBNI) */
    qrMessage: string;
  };

  /** Dynamic schema and settings driving the RSVP form */
  rsvpForm: {
    title: string;
    description: string;
    submitButtonText: string;
    sendingText: string;
    successMessage: {
      title: string;
      subtitle: string;
      morseCode: string;
    };
    errorMessage: string;
    schema: FormSection[];
  };
  
  /** Dress code parameters and shoe suggestions */
  dressCode: {
    title: string;
    main: string;
    detail: string;
    subDetail: string;
  };
}

export const weddingContent: WeddingContent = {
  // ==========================================
  // SEO & METADATA GUIDELINES:
  // Edit these values to optimize how your site displays in search engines.
  // ==========================================
  metaTitle: "Naše Svatba | Hanka & Filip",
  metaDescription: "Hanka a Filip se berou! 15. srpna 2026 ve Šlapanicích. Těšíme se na vás.",

  // ==========================================
  // HERO SECTION GUIDELINES:
  // Adjust the text shown on the giant welcoming screen.
  // ==========================================
  hero: {
    title: "Bereme se!",
    subtitle: "Budeme moc rádi, když u toho budete s námi.",
    buttonText: "Potvrdit účast",
  },

  // ==========================================
  // ABOUT US SECTION GUIDELINES:
  // - You can add formatting tags like `<span class="font-bold">` within paragraphs.
  // - Gallery layouts are automatically optimized using dense flow to eliminate holes.
  // ==========================================
  aboutUs: {
    title: "O nás",
    motto: "Příběh dvou teček, které v šifrách života našly svou společnou čárku.",
    sections: [
      {
        id: "mywalove",
        title: "Proč mywalove.cz?",
        content: [
          "Filip má kvůli svému příjmení (Valášek) přezdívku Wal. Po svatbě budou oba Valáškovi, tedy tak trochu Walovi. 😊 Název MyWalove pak můžete číst různě: jako My Walové, Mývalové nebo třeba MyWa.Love. Necháme to na vás."
        ]
      },
      {
        id: "hrachovina",
        title: "Proč Hrachovina a Filipíny?",
        content: [
          "Hanka a Filip rádi chodí na šifrovačky. Hrachovina a Filipíny jsou pomocná slova pro zápis morseovky, kde tečka reprezentuje krátký tón/slabiku a čárka dlouhý tón/slabiku (H: ····, F ··-·). Jak jste si asi všimli ve svatebním oznámení (nebo tady na webu), slovo Hrachovina obsahuje všechna písmena jména HANA a slovo FILIPíny všechna písmena jména FILIP, v obou případech ve správném pořadí. A to nemůže být náhoda!",
          "Pokud bychom chtěli hledat souvislosti ještě dál, Hanka studovala genetiku a hrachovina může připomínat Mendelovy pokusy s hrachem. A Filip studoval matematiku a ve slově Filipíny lze najít i π."
        ]
      }
    ],
    gallery: [
      { src: imgLublan, alt: "V Lublani", size: "large" },
      { src: imgSifrovacka, alt: "Na šifrovačce", size: "small" },
      { src: imgVytah2, alt: "Ve výtahu", size: "vertical" },
      {
        src: null,
        alt: "",
        type: "text",
        title: "Mývalové z Brna",
        detail: "Společně luštíme šifru života",
        size: "small",
      },
      { src: imgSaline, alt: "V šalině", size: "horizontal" },
      { src: imgPlac, alt: "Společný pláč", size: "horizontal" },
      { src: imgMyvali, alt: "My jsme mývalové", size: "vertical" },
      { src: imgFabar, alt: "V F.A. baru", size: "horizontal" },
      { src: imgVytah, alt: "Ve výtahu", size: "small" },
      { src: imgStehovani, alt: "Malování po stěhování", size: "large" },
      { src: imgSvetry, alt: "Ve vánočních svetrech", size: "vertical" },
      { src: imgTmou, alt: "Na šifrovačce Tmou", size: "vertical" },
      { src: imgViden, alt: "Ve Vídni", size: "horizontal" },
      { src: imgParek, alt: "Na Párku", size: "vertical" },
      { src: imgWuppertal, alt: "Ve Wuppertalu", size: "horizontal" },
      { src: imgMore, alt: "U moře", size: "small" },
      { src: imgCap, alt: "U Čápa", size: "horizontal" },
      { src: imgSbeerka, alt: "Ve Sbeerce", size: "horizontal" },
      { src: imgKokorinsko, alt: "Pod Kokořínem", size: "horizontal" },
      { src: imgKokorinsko2, alt: "Pořád pod Kokořínem", size: "horizontal" },
    ],
  },

  // ==========================================
  // VENUE & MAP GUIDELINES:
  // - Coordinates can be taken from Google Maps URL, representing [Latitude, Longitude].
  // - Map pins are rendered dynamically with modern custom SVG icons.
  // ==========================================
  whenWhere: {
    title: "Kdy a kde",
    venueName: "Sokec, Šlapanice",
    address: "Nádražní 87, 664 51 Šlapanice",
    coords: [49.1605206, 16.7286136],
    googleMapsUrl: "https://maps.app.goo.gl/AJ5MkMekiaeEhSGf6",
    description: "Sokec je taková fajn restaurace pod Sokolovnou, před kterou je dobrej plácek na párty a Filipova sestra už tam svatbu měla a bylo to fajn.",
    transportOptions: [
      {
        id: "car",
        label: "Autem",
        icon: "car",
        morse: "·−·−·−·−·−·−·−·−",
        title: "Doprava autem",
        detail: "Parkování přímo u Sokecu nebo v přilehlých ulicích. Pozor ale na to, že nelze zaparkovat na ulici Nádražní a auto tam nechat do druhého dne. V neděli má být v rámci Šlapanických slavností na ulici Nádraždní průvod a zákaz zastavení.",
        marker: {
          coords: [49.1594822, 16.7289861],
          title: "Parkoviště u Sokecu",
          icon: "parking",
        },
      },
      {
        id: "train",
        label: "Vlakem",
        icon: "train",
        morse: "···−···−···−···−",
        title: "Vlakem (Linka S6)",
        detail: "Z hlavního nádraží v Brně (linka S6) na stanici Šlapanice. Sokec se nachází pouhých 5 minut pohodlné chůze od nádraží.",
        marker: {
          coords: [49.1567917, 16.7294883],
          title: "Vlakové nádraží Šlapanice",
          icon: "train",
        },
      },
      {
        id: "bus",
        label: "Trolejbusem",
        icon: "bus",
        morse: "----------------",
        title: "Trolejbusem (Linka 31)",
        detail: "Přímé trolejbusové spojení linkou 31 z Hlavního nádraží Brno na zastávku Šlapanice Kalvodova, odkud je to k Sokecu 10 minut chůze.",
        marker: {
          coords: [49.1664506, 16.7262975],
          title: "Zastávka Šlapanice Kalvodova",
          icon: "bus",
        },
      },
      {
        id: "night-bus",
        label: "Domů",
        icon: "bus",
        morse: "----------------",
        title: "Rozjezdem (linka N96)",
        detail: "Ze Šlapanic se v noci dostanete zpátky do Brna rozjezdem N96, který jezdí ze zastávky Šlapanice, Kalvodova. Od Sokecu je to na Kalvodovu asi 10 minut chůze.",
        marker: {
          coords: [49.1664506, 16.7262975],
          title: "Zastávka Šlapanice Kalvodova",
          icon: "bus",
        },
      },
    ],
  },

  // ==========================================
  // SCHEDULE GUIDELINES:
  // - Timeline nodes automatically alternate styles.
  // - Feel free to add or delete blocks; they render dynamically.
  // ==========================================
  schedule: {
    title: "Harmonogram",
    items: [
      {
        time: "13:00",
        title: "Rodinný oběd",
        description: "",
      },
      {
        time: "14:30",
        title: "Příprava na obřad",
        description: "příchod a přivítaní hostů",
      },
      {
        time: "15:00",
        title: "Obřad",
        description: "",
      },
      {
        time: "15:30",
        title: "Oslava",
        description: "Až do konce!",
      },
    ],
  },

  // ==========================================
  // GIFTS & BANKING GUIDELINES:
  // - Keep format "prefix-account / bank" for dynamic QR payment generators.
  // - Keep message uppercase and without accents (CZ SPAYD standard).
  // ==========================================
  gifts: {
    title: "Svatební dary",
    heading: "Největším darem pro nás bude vaše přítomnost.",
    description: "Pokud byste nás přesto chtěli obdarovat, budeme rádi za příspěvek do rodinné kasičky. Pro ty, kteří nechtějí řešit hotovost, přikládáme QR kód. Neberte to ale jako vstupné na svatbu. 😊 Jen předpokládáme, že si někteří z vás budou lámat hlavu nad tím, co nám pořídit, a tak vám chceme rozhodování co nejvíce usnadnit.",
    accountLabel: "Číslo bankovního účtu",
    accountNumber: "670100-2223828816 / 6210",
    accountNote: "Při platbě prosím uveďte do poznámky vaše jména, ať víme, komu poděkovat.",
    qrLabel: "Rychlá QR platba",
    qrMessage: "DAR SVATEBNI",
  },

  // ==========================================
  // RSVP FORM GUIDELINES:
  // - You can customize labels, placeholders, errors, and success actions.
  // - The dynamic schema drives the HTML form rendering and interactive validation!
  // ==========================================
  rsvpForm: {
    title: "Účast",
    description: "Prosíme o potvrzení účasti do 30. června 2026. Každý dospělý host vyplňuje formulář zvlášť, děti vyplňuje jen jeden z rodičů.",
    submitButtonText: "Odeslat potvrzení",
    sendingText: "Odesílám...",
    successMessage: {
      title: "Děkujeme!",
      subtitle: "Vaše odpověď byla bezpečně uložena. Těšíme se na vás 15. srpna ve Šlapanicích!",
      morseCode: "··− &nbsp; −·−·  &nbsp; ·−  &nbsp; ···  &nbsp; −"
    },
    errorMessage: "Chyba při odesílání. Zkuste to prosím znovu.",
    schema: [
      {
        section: "personal",
        grid: true,
        fields: [
          {
            id: "name",
            name: "name",
            label: "Jméno a příjmení",
            type: "text",
            required: true,
            placeholder: "Jan Novák",
            condition: null,
            options: [],
          },
          {
            id: "email",
            name: "email",
            label: "E-mail",
            type: "email",
            required: true,
            placeholder: "jan@seznam.cz",
            condition: null,
            options: [],
          },
        ],
      },
      {
        section: "attendance",
        fields: [
          {
            id: "attendance",
            name: "attendance",
            label: "Dorazíte?",
            type: "radio",
            condition: null,
            required: true,
            placeholder: null,
            options: [
              { value: "ano", label: "Ano, rád/a", checked: true },
              { value: "ne", label: "Bohužel ne", checked: false },
            ],
          },
        ],
      },
      {
        section: "children",
        divider: true,
        grid: true,
        fields: [
          {
            id: "coming-with-children",
            name: "coming_with_children",
            label: "Přijdete s dětmi?",
            type: "checkbox",
            text: "Ano, beru s sebou ratolesti",
            condition: null,
            required: false,
            placeholder: null,
            options: [],
          },
          {
            id: "how-many-children",
            name: "how_many_children",
            label: "Kolik jich bude? Kolik jim je let? Co je baví?",
            type: "text",
            condition: "coming-with-children",
            required: false,
            placeholder: "např. 2 děti (4 a 7 let), rády kreslí...",
            options: [],
          },
        ],
      },
      {
        section: "lunch",
        divider: true,
        fields: [
          {
            id: "is-lunch-guest",
            name: "is_lunch_guest",
            label: "Jste pozváni na rodinný oběd?",
            type: "checkbox",
            text: "Ano, patřím do rodinného kruhu",
            condition: null,
            required: false,
            placeholder: null,
            options: [],
          },
          {
            id: "coming-to-lunch",
            name: "coming_to_lunch",
            label: "Dorazíte na oběd?",
            type: "radio",
            condition: "is_lunch_guest",
            conditionValue: null,
            required: false,
            placeholder: null,
            options: [
              { value: "yes", label: "Ano, s radostí", checked: false },
              { value: "no", label: "Bohužel se sejdu až u obřadu", checked: false },
            ],
          },
        ],
      },
      {
        section: "additional",
        divider: true,
        fields: [
          {
            id: "diet",
            name: "diet",
            label: "Alergie / Dietní omezení (napište také, co mají nejraději děti, pokud mají specifické chutě)",
            type: "text",
            placeholder: "např. bezlepková dieta, vegetarián, bez ořechů...",
            condition: null,
            required: false,
            options: [],
          },
        ],
      },
    ],
  },

  // ==========================================
  // DRESS CODE GUIDELINES:
  // Guidelines regarding wedding fashion and shoe choices.
  // ==========================================
  dressCode: {
    title: "Dress Code",
    main: "žádný",
    detail: "Přijďte v tom, v čem se cítíte dobře!",
    subDetail: "",
  },
};
