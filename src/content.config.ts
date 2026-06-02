import { defineCollection, z } from "astro:content";
import { glob } from "astro/loaders";

const wedding = defineCollection({
  loader: glob({ pattern: "**/[^_]*.{yaml,yml}", base: "./src/content/wedding" }),
  schema: ({ image }) =>
    z.object({
      metaTitle: z.string(),
      metaDescription: z.string(),
      hero: z.object({
        title: z.string(),
        date: z.string(),
        subtitle: z.string(),
        morseCode: z.string(),
        morseCodeText: z.string(),
        buttonText: z.string(),
      }),
      aboutUs: z.object({
        title: z.string(),
        motto: z.string(),
        sections: z.array(
          z.object({
            id: z.string(),
            title: z.string(),
            content: z.array(z.string()),
          })
        ),
        gallery: z.array(
          z.union([
            z.object({
              src: image(),
              alt: z.string(),
              size: z.enum(["small", "large", "vertical", "horizontal"]),
              type: z.literal("image").optional(),
            }),
            z.object({
              src: z.null(),
              alt: z.string(),
              type: z.literal("text"),
              title: z.string(),
              detail: z.string(),
              size: z.enum(["small", "large", "vertical", "horizontal"]),
            }),
          ])
        ),
      }),
      whenWhere: z.object({
        title: z.string(),
        venueName: z.string(),
        address: z.string(),
        coords: z.tuple([z.number(), z.number()]),
        googleMapsUrl: z.string(),
        description: z.string(),
        transportOptions: z.array(
          z.object({
            id: z.string(),
            label: z.string(),
            icon: z.enum(["car", "train", "bus"]),
            morse: z.string(),
            morseText: z.string(),
            title: z.string(),
            detail: z.string(),
            marker: z.object({
              coords: z.tuple([z.number(), z.number()]),
              title: z.string(),
              icon: z.enum(["parking", "train", "bus"]),
            }),
          })
        ),
      }),
      schedule: z.object({
        title: z.string(),
        items: z.array(
          z.object({
            time: z.string(),
            title: z.string(),
            description: z.string(),
          })
        ),
      }),
      gifts: z.object({
        title: z.string(),
        heading: z.string(),
        description: z.string(),
        accountLabel: z.string(),
        accountNumber: z.string(),
        accountNote: z.string(),
        qrLabel: z.string(),
        qrMessage: z.string(),
      }),
      rsvpForm: z.object({
        title: z.string(),
        description: z.string(),
        rsvpUrl: z.string().optional(),
        submitButtonText: z.string(),
        sendingText: z.string(),
        successMessage: z.object({
          title: z.string(),
          subtitle: z.string(),
          morseCode: z.string(),
        }),
        errorMessage: z.string(),
        schema: z.array(
          z.object({
            section: z.string(),
            grid: z.boolean().optional(),
            divider: z.boolean().optional(),
            fields: z.array(
              z.object({
                id: z.string(),
                name: z.string(),
                label: z.string(),
                type: z.enum(["text", "email", "radio", "select", "checkbox"]),
                required: z.boolean(),
                placeholder: z.string().nullable(),
                text: z.string().optional(),
                condition: z.string().nullable(),
                conditionValue: z.string().nullable().optional(),
                options: z
                  .array(
                    z.object({
                      value: z.string(),
                      label: z.string(),
                      checked: z.boolean(),
                    })
                  )
                  .optional(),
              })
            ),
          })
        ),
      }),
      dressCode: z.object({
        title: z.string(),
        main: z.string(),
        detail: z.string(),
        subDetail: z.string(),
      }),
      morseMessage: z.object({
        buttonText: z.string(),
        title: z.string(),
        description: z.string(),
        placeholderName: z.string(),
        submitButtonText: z.string(),
        sendingText: z.string(),
        successMessage: z.string(),
        errorMessage: z.string(),
      }),
    }),
});

export const collections = { wedding };
