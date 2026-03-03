-- Lua filter: convert pandoc tables to simple LaTeX tabular (multicol-compatible)
function Table(tbl)
  local aligns = {}
  for _, spec in ipairs(tbl.colspecs) do
    local a = spec[1]
    if a == "AlignRight" then
      table.insert(aligns, "r")
    elseif a == "AlignCenter" then
      table.insert(aligns, "c")
    else
      table.insert(aligns, "l")
    end
  end

  local result = "\\begin{tabular}{" .. table.concat(aligns, " ") .. "}\n\\hline\n"

  -- Header rows
  if tbl.head and tbl.head.rows then
    for _, row in ipairs(tbl.head.rows) do
      local cells = {}
      for _, cell in ipairs(row.cells) do
        table.insert(cells, "\\textbf{" .. pandoc.utils.stringify(cell.contents) .. "}")
      end
      result = result .. table.concat(cells, " & ") .. " \\\\\n\\hline\n"
    end
  end

  -- Body rows
  for _, body in ipairs(tbl.bodies) do
    for _, row in ipairs(body.body) do
      local cells = {}
      for _, cell in ipairs(row.cells) do
        table.insert(cells, pandoc.utils.stringify(cell.contents))
      end
      result = result .. table.concat(cells, " & ") .. " \\\\\n"
    end
  end

  result = result .. "\\hline\n\\end{tabular}"
  return pandoc.RawBlock("latex", result)
end
