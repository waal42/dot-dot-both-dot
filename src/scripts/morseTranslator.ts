// src/scripts/morseTranslator.ts

export const MORSE_DICT: Record<string, string> = {
  "A": "·−",
  "B": "−···",
  "C": "−·−·",
  "D": "−··",
  "E": "·",
  "F": "··−·",
  "G": "−−·",
  "H": "····",
  "CH": "−−−−", // Special Czech Morse Character
  "I": "··",
  "J": "·−−−",
  "K": "−·−",
  "L": "·−··",
  "M": "−−",
  "N": "−·",
  "O": "−−−",
  "P": "·−−·",
  "Q": "−−·−",
  "R": "·−·",
  "S": "···",
  "T": "−",
  "U": "··−",
  "V": "···−",
  "W": "·−−",
  "X": "−··−",
  "Y": "−·−−",
  "Z": "−−··",
  "0": "−−−−−",
  "1": "·−−−−",
  "2": "··−−−",
  "3": "···−−",
  "4": "····−",
  "5": "·····",
  "6": "−····",
  "7": "−−···",
  "8": "−−−··",
  "9": "−−−−·",
  ".": "·−·−·−",
  ",": "−−··−−",
  "?": "··−−··",
  "!": "−−·−−−"
};

// Create an inverted dictionary for fast decoding
export const REVERSE_MORSE_DICT: Record<string, string> = Object.fromEntries(
  Object.entries(MORSE_DICT).map(([letter, code]) => [code, letter])
);

/**
 * Standardizes characters, strips accents/diacritics, maps CH to its custom code,
 * and outputs Morse blocks separated by ' / ' (letters) and ' // ' (words).
 */
export function textToMorse(text: string): string {
  if (!text) return "";

  // 1. Normalize diacritics & uppercase
  let normalized = text
    .toUpperCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, ""); // remove czech accents (ěščřž... -> escrz)

  // 2. Translate words
  const words = normalized.trim().split(/\s+/);
  const translatedWords: string[] = [];

  for (const word of words) {
    const translatedChars: string[] = [];
    let i = 0;

    while (i < word.length) {
      // Check for 'CH' lookahead (Czech Morse digraph)
      if (i + 1 < word.length && word[i] === "C" && word[i + 1] === "H") {
        translatedChars.push(MORSE_DICT["CH"]);
        i += 2;
      } else {
        const char = word[i];
        if (MORSE_DICT[char]) {
          translatedChars.push(MORSE_DICT[char]);
        }
        i++;
      }
    }

    if (translatedChars.length > 0) {
      translatedWords.push(translatedChars.join(" / "));
    }
  }

  return translatedWords.join(" // ");
}

/**
 * Decodes a Morse code string back into normalized Latin text.
 * Expects letters separated by single slashes '/' and words separated by double slashes '//'.
 */
export function morseToText(morse: string): string {
  if (!morse) return "";

  // Standardize potential inputs (dots can be . or ·, dashes can be -, –, −)
  const cleanMorse = morse
    .replace(/\./g, "·")
    .replace(/-/g, "−")
    .replace(/–/g, "−");

  // Words are separated by double slashes (e.g. "//" or " // ")
  const words = cleanMorse.trim().split(/\s*\/\/\s*/);
  const decodedWords: string[] = [];

  for (const word of words) {
    // Letters within a word are separated by single slashes (e.g. "/" or " / ")
    const letters = word.split(/\s*\/\s*/);
    const decodedChars: string[] = [];

    for (const letter of letters) {
      const cleanLetter = letter.trim();
      if (REVERSE_MORSE_DICT[cleanLetter]) {
        decodedChars.push(REVERSE_MORSE_DICT[cleanLetter]);
      }
    }

    if (decodedChars.length > 0) {
      decodedWords.push(decodedChars.join(""));
    }
  }

  return decodedWords.join(" ");
}

