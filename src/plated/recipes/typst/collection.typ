// Typst template for recipe collections
// Call like this:
//  typst compile collection.typ --input 'data={"collection": "collection.json"}'

#let primary_colour = rgb("#ce1f36")
#let text_colour = rgb("#333")

// Font constants
#let body_font = "Libertinus Serif"
#let title_font = "DejaVu Sans"
#let heading_font = "DejaVu Sans"

#set page(
  margin: (x: 54pt, y: 52pt),
  numbering: "1",
  number-align: right,
  fill: rgb("ede8d0"),
)

#set text(10pt, font: body_font, fill: text_colour)

#let collection_from_json(data) = {
  let collection_data = json(data.collection)

  // Title page
  align(center)[
    #v(150pt)
    #text(fill: primary_colour, font: title_font, size: 36pt, weight: 100, upper(collection_data.name))
    #v(10pt)

    #if collection_data.at("description", default: "") != "" {
      text(size: 12pt, emph(collection_data.description))
    }

    #v(20pt)
    #text(size: 11pt, fill: text_colour.lighten(30%))[
      #collection_data.recipes.len() recipe#if collection_data.recipes.len() != 1 [s]
    ]

    #v(150pt)
  ]

  pagebreak()

  // Table of contents
  align(center)[
    #text(fill: primary_colour, font: heading_font, size: 20pt, weight: 300)[Table of Contents]
    #v(10pt)
  ]

  set par(leading: 0.8em)

  for (idx, recipe) in collection_data.recipes.enumerate() {
    grid(
      columns: (1fr, auto),
      text(size: 11pt)[#recipe.title], text(size: 11pt, fill: primary_colour)[#(idx + 3)],
    )
    v(0.3em)
  }

  // Recipe pages
  for recipe in collection_data.recipes {
    pagebreak()

    // Recipe title
    text(fill: primary_colour, font: title_font, size: 24pt, weight: 200, upper(recipe.title))

    v(5pt)

    // Description
    if recipe.at("description", default: "") != "" {
      emph(recipe.description)
      v(10pt)
    }

    // Metadata grid
    grid(
      columns: (1fr, 1fr, 1fr),
      column-gutter: 10pt,
      [
        #text(fill: primary_colour, weight: "bold")[Servings:] #recipe.at("servings", default: 1)
      ],
      [
        #if recipe.at("prep_time_minutes", default: 0) > 0 {
          [#text(fill: primary_colour, weight: "bold")[Prep:] #recipe.prep_time_minutes min]
        }
      ],
      [
        #if recipe.at("wait_time_minutes", default: 0) > 0 {
          [#text(fill: primary_colour, weight: "bold")[Cook:] #recipe.wait_time_minutes min]
        }
      ],
    )

    v(15pt)

    // Ingredients
    text(fill: primary_colour, font: heading_font, size: 14pt, weight: "bold")[Ingredients]
    v(5pt)

    for ingredient in recipe.ingredients {
      let amount = ingredient.at("amount", default: "")
      let unit = ingredient.at("unit", default: "")
      let name = ingredient.name
      let note_text = if ingredient.at("note", default: "") != "" { footnote(ingredient.note) } else { "" }

      set list(tight: false, marker: [•])
      set par(spacing: 0.5em)

      if amount != "" and unit != "" {
        list([#amount #unit #name#note_text])
      } else if amount != "" {
        list([#amount #name#note_text])
      } else {
        list([#name#note_text])
      }
    }

    v(10pt)

    // Instructions
    text(fill: primary_colour, font: heading_font, size: 14pt, weight: "bold")[Instructions]
    v(5pt)

    set enum(
      numbering: n => text(
        fill: primary_colour,
        font: heading_font,
        size: 12pt,
        weight: "bold",
        str(n),
      ),
    )
    set par(justify: true)
    set enum(spacing: 0.8em)

    for step in recipe.steps {
      enum.item()[#step.content]
    }

    // Notes
    if recipe.at("notes", default: "") != "" {
      v(10pt)
      text(fill: primary_colour, font: heading_font, size: 12pt, weight: "bold")[Chef's Tips]
      v(5pt)
      emph(recipe.notes)
    }
  }
}

#collection_from_json(json(bytes(sys.inputs.data)))
