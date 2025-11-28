// Typst template for meal plans
// Call like this:
//  typst compile meal_plan.typ --input 'data={"meal_plan": "meal_plan.json"}'

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

#let meal_plan_from_json(data) = {
  let plan_data = json(data.meal_plan)

  // Title page
  align(center)[
    #v(150pt)
    #text(fill: primary_colour, font: title_font, size: 36pt, weight: 100, upper(plan_data.name))
    #v(10pt)

    #if plan_data.at("description", default: "") != "" {
      text(size: 12pt, emph(plan_data.description))
    }

    #v(20pt)
    #text(size: 11pt, fill: text_colour.lighten(30%))[
      #plan_data.start_date to #plan_data.end_date
    ]

    #v(150pt)
  ]

  pagebreak()

  // Group entries by date
  let dates = ()
  for entry in plan_data.entries {
    if entry.date not in dates {
      dates.push(entry.date)
    }
  }

  // Display each day
  for date in dates {
    // Day header
    text(fill: primary_colour, font: heading_font, size: 18pt, weight: "bold")[
      #datetime(
        year: int(date.slice(0, 4)),
        month: int(date.slice(5, 7)),
        day: int(date.slice(8, 10)),
      ).display("[weekday repr:long], [month repr:long] [day], [year]")
    ]

    v(10pt)

    // Get entries for this date
    let day_entries = plan_data.entries.filter(e => e.date == date)

    // Group by meal type
    let meal_types = ("breakfast", "lunch", "dinner", "snack")
    let meal_labels = (
      "breakfast": "Breakfast",
      "lunch": "Lunch",
      "dinner": "Dinner",
      "snack": "Snack",
    )

    for meal_type in meal_types {
      let meals = day_entries.filter(e => e.meal_type == meal_type)

      if meals.len() > 0 {
        text(fill: primary_colour, font: heading_font, size: 12pt, weight: "bold")[
          #meal_labels.at(meal_type)
        ]
        v(5pt)

        for meal in meals {
          box(
            width: 100%,
            fill: white,
            stroke: 0.5pt + primary_colour.lighten(60%),
            radius: 4pt,
            inset: 10pt,
            [
              #grid(
                columns: (1fr, auto),
                [
                  #text(weight: "bold")[#meal.recipe_title]
                  #if meal.servings > 1 {
                    [ (#meal.servings servings)]
                  }
                ],
                [
                  #if meal.at("prep_time_minutes", default: 0) > 0 or meal.at("wait_time_minutes", default: 0) > 0 {
                    text(fill: text_colour.lighten(30%), size: 9pt)[
                      #if meal.at("prep_time_minutes", default: 0) > 0 {
                        [⏱ #meal.prep_time_minutes min]
                      }
                    ]
                  }
                ],
              )
              #if meal.at("notes", default: "") != "" {
                v(5pt)
                text(size: 9pt, fill: text_colour.lighten(20%))
                emph(meal.notes)
              }
            ],
          )
          v(7pt)
        }

        v(10pt)
      }
    }

    v(20pt)
    line(length: 100%, stroke: 0.5pt + primary_colour.lighten(50%))
    v(20pt)
  }
}

#meal_plan_from_json(json(bytes(sys.inputs.data)))
