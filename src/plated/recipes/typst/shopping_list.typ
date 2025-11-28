// Typst template for shopping lists
// Call like this:
//  typst compile shopping_list.typ --input 'data={"shopping_list": "shopping_list.json"}'

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

#let shopping_list_from_json(data) = {
  let list_data = json(data.shopping_list)

  // Title page
  align(center)[
    #v(100pt)
    #text(fill: primary_colour, font: title_font, size: 36pt, weight: 100)[SHOPPING LIST]
    #v(10pt)

    #text(fill: primary_colour, font: heading_font, size: 18pt, weight: 300)[
      #list_data.meal_plan_name
    ]

    #v(10pt)
    #text(size: 11pt, fill: text_colour.lighten(30%))[
      #list_data.start_date to #list_data.end_date
    ]

    #v(100pt)
  ]

  pagebreak()

  // Shopping list items
  text(fill: primary_colour, font: heading_font, size: 20pt, weight: "bold")[Ingredients]
  v(15pt)

  // Group ingredients alphabetically
  for ingredient in list_data.ingredients {
    box(
      width: 100%,
      fill: white,
      stroke: 0.5pt + primary_colour.lighten(60%),
      radius: 4pt,
      inset: 10pt,
      [
        #grid(
          columns: (20pt, 1fr, auto),
          column-gutter: 10pt,
          [
            // Checkbox
            #box(
              width: 15pt,
              height: 15pt,
              stroke: 1pt + primary_colour.lighten(40%),
              radius: 2pt,
            )
          ],
          [
            // Ingredient name
            #text(weight: "bold", size: 11pt)[#ingredient.name]

            // Recipe references
            #v(3pt)
            #for item in ingredient.items {
              text(size: 8pt, fill: text_colour.lighten(30%))[
                • #item.recipe (#item.amount #item.unit)
              ]
              linebreak()
            }
          ],
          [
            // Total amount
            #if ingredient.at("total_amount", default: "") != "" {
              text(fill: primary_colour, size: 11pt, weight: "bold")[
                #ingredient.total_amount
              ]
            }
          ]
        )
      ]
    )
    v(8pt)
  }

  v(30pt)

  // Summary
  line(length: 100%, stroke: 0.5pt + primary_colour.lighten(50%))
  v(10pt)

  text(fill: text_colour.lighten(20%), size: 9pt)[
    Total: #list_data.ingredients.len() ingredient#if list_data.ingredients.len() != 1 [s] from #list_data.recipe_count recipe#if list_data.recipe_count != 1 [s]
  ]
}

#shopping_list_from_json(json(bytes(sys.inputs.data)))
