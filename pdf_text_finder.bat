set "LOG=D:\kadam\Documents\pdf_find_replace_by_coordinates\terminal_print_logs\pdf_text_finder.txt"
set "TMP=%LOG%.new"

python "D:\kadam\Documents\pdf_find_replace_by_coordinates\replacement_engine\pdf_text_finder.py" --config finder_config.json >_ 2>&1 && (
  rem build new log = new output + blank line + old log (if exists)
  if exist "%TMP%" del "%TMP%"
  type _ > "%TMP%"
  echo.>>"%TMP%"
  if exist "%LOG%" type "%LOG%" >> "%TMP%"
  move /Y "%TMP%" "%LOG%" >nul
  del _
  notepad "%LOG%"
)
