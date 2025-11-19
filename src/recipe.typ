//Inspired by https://github.com/maxdinech/typst-recipe
// Call like this:
//  typst compile recipe.typ --input 'data={"recipe": "recipe2.json", "image": "image.jpg"}'


#let primary_colour = rgb("#ce1f36")
#let text_colour = rgb("#333")

// Font constants
#let body_font = "Libertinus Serif"
#let title_font = "DejaVu Sans"
#let author_font = "DejaVu Sans"
#let heading_font = "DejaVu Sans"

#let image-height = 15em

#set page(
  margin: (x: 54pt, y: 52pt),
  numbering: "1",
  number-align: right,
  fill: rgb("ede8d0"),
)

#let recipes(title, doc) = {
  set text(10pt, font: body_font)

  text(fill: primary_colour, font: title_font, size: 30pt, weight: 100, title)
  set align(left)

  show heading.where(level: 1): it => [
    #pagebreak()
    #v(300pt)
    #set align(center)
    #text(
      fill: primary_colour,
      font: heading_font,
      weight: 300,
      size: 20pt,
      { it.body },
    )
    #text(" ")
    #pagebreak()
  ]
  doc
}

#let format_ingredient(ingredient) = {
  set list(tight: false)
  set par(spacing: 0.8em, leading: 0.3em)

  let amount = ingredient.at("amount", default: "")
  let unit = ingredient.at("unit", default: "")
  let food = ingredient.name
  let note_text = if ingredient.at("note", default: "") != "" { footnote(ingredient.note) } else { "" }

  if amount != "" and unit != "" {
    [- #amount #unit #food#note_text]
  } else if amount != "" {
    [- #amount #food#note_text]
  } else {
    [- #food#note_text]
  }
}

#let display_ingredients_list(ingredients) = {
  //  panic(ingredients)

  //  grid(
  //    columns: (2fr, 1fr),
  //    gutter: .5em,
  //    ..ingredients
  //      .map(it => (
  //        it.food.name + { if (it.note != none) { (footnote(it.note)) } else { "" } },
  //        str(it.amount) + " " + it.unit.name,
  //      ))
  //      .flatten(),
  //  )

  for ingredient in ingredients {
    format_ingredient(ingredient)
  }
}

#let display_steps_list(steps) = {
  set enum(
    numbering: n => text(
      fill: primary_colour,
      font: heading_font,
      size: 14pt,
      weight: "bold",
      str(n),
    ),
  )
  for step in steps {
    enum.item()[#step.content]
  }
}

#let display_ingredients(ingredients) = {
  emph(display_ingredients_list(ingredients))
}

#let display_steps(steps) = {
  [== Preparation]
  set par(justify: true)
  set enum(spacing: 1em)
  display_steps_list(steps)
}


#let display_pairings(pairings) = {
  [== Pairing Suggestions]
  emph(pairings)
}


#let recipe(
  title: "",
  author: "",
  description: "",
  image_path: "",
  servings: 1,
  servings_text: "",
  working_time: "",
  waiting_time: "",
  ingredients: (),
  steps: [],
  remarks: [],
  pairings: [],
) = {
  show heading.where(level: 2): it => text(
    fill: primary_colour,
    font: heading_font,
    weight: 300,
    size: 11pt,
    grid(
      columns: (auto, auto),
      column-gutter: 5pt,
      [#{ upper(it.body) }],
      [
        #v(5pt)
        #line(length: 100%, stroke: 0.4pt + primary_colour)
      ],
    ),
  )

  {
    grid(
      columns: (380pt, 100pt),
      [
        #text(fill: primary_colour, font: title_font, size: 24pt, weight: 200, upper(title))
        #h(3pt)
        #text(fill: text_colour, font: author_font, size: 20pt, author)
        #v(0pt)
        #emph(description)
      ],
      [
        #v(2pt)
        #set align(right)
        #if (working_time != "") {
          [_Preparation: #working_time _]
        }
        #if (waiting_time != "") {
          [\ _Waiting: #waiting_time _]
        }
      ],
    )

    // Display image if it exists
    if image_path != "" {
      context { place(image(image_path, width: page.width, height: image-height), dx: -page.margin.left) }
      v(image-height + 2em)
    }

    grid(
      columns: (90pt, 380pt),
      column-gutter: 15pt,
      [
        #set list(marker: [], body-indent: 0pt)
        #set align(right)
        #text(fill: primary_colour, font: heading_font, weight: 300, size: 11pt, upper([Ingredients\ ]))
        #[#servings servings]
        #servings_text

        #display_ingredients(ingredients)
      ],
      [
        #display_steps(steps)
        #if remarks != [] {
          [== Chef's Tips]
          emph(remarks)
        }
        #if pairings != [] {
          display_pairings(pairings)
        }
      ],
    )
    v(30pt)
  }
}

#let recipe_from_json(data) = {
  let recipe_data = json(data.recipe)

  let all_ingredients = recipe_data.ingredients

  let prep_time = if recipe_data.at("prep_time_minutes", default: none) != none and recipe_data.prep_time_minutes > 0 {
    str(recipe_data.prep_time_minutes) + " min"
  } else { "" }

  let wait_time = if recipe_data.at("wait_time_minutes", default: none) != none and recipe_data.wait_time_minutes > 0 {
    str(recipe_data.wait_time_minutes) + " min"
  } else { "" }

  // Check if image.jpg exists and include it
  let image_path = data.at("image", default: "")

  let remarks_text = recipe_data.at("notes", default: "")
  let remarks_list = if remarks_text != "" { (remarks_text,) } else { () }

  recipe(
    title: recipe_data.title,
    description: recipe_data.at("description", default: ""),
    servings: recipe_data.at("servings", default: 1),
    servings_text: "",
    working_time: prep_time,
    waiting_time: wait_time,
    ingredients: all_ingredients,
    steps: recipe_data.steps,
    remarks: remarks_list,
    image_path: image_path,
  )
}

#recipe_from_json(json(bytes(sys.inputs.data)))
