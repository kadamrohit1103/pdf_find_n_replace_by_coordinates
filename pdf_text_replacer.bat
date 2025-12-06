set "LOGDIR=D:\kadam\Documents\pdf_find_replace_by_coordinates\terminal_print_logs"
set "LOG=%LOGDIR%\pdf_text_replacer.txt"
set "TMP=%LOGDIR%\pdf_text_replacer.new"
set "RUN=%LOGDIR%\_"

python "D:\kadam\Documents\pdf_find_replace_by_coordinates\replacement_engine\pdf_text_replacer.py" --config replacements.json --verbose >"%RUN%" 2>&1 && (
  rem New log = latest run + blank line + old log
  if exist "%TMP%" del "%TMP%"
  type "%RUN%" > "%TMP%"
  echo.>>"%TMP%"
  if exist "%LOG%" type "%LOG%" >> "%TMP%"
  move /Y "%TMP%" "%LOG%" >nul

  del "%RUN%"
  notepad "%LOG%"
)
