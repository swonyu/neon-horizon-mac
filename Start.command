#!/bin/zsh
set -eu
cd -- "${0:A:h}"
if ! command -v python3 >/dev/null 2>&1; then
  print 'Python 3 is needed for the optional setup tool. The wallpaper and manual guide work without it.'
  print 'Download Python from https://www.python.org/downloads/macos/ or use docs/SETUP.md.'
  read 'answer?Press Return to close. '
  exit 1
fi
print 'Neon Horizon — Mac Makeover'
print '1  Preview the complete preset (changes nothing)'
print '2  Apply the complete preset, including 7-day clipboard history and Option Hot Corners'
print '3  Undo a previous preset run'
print '4  Open the wallpaper preview'
print '5  Open the setup guide'
read 'choice?Choose 1–5 [1]: '
case "${choice:-1}" in
  1) python3 makeover.py plan --groups all ;;
  2) python3 makeover.py plan --groups all
     read 'answer?Save a backup and apply these settings? Type yes: '
     if [[ "$answer" == yes ]]; then python3 makeover.py apply --groups all; fi ;;
  3) python3 makeover.py backups
     read 'backup?Paste the full backup path above, or Return to cancel: '
     if [[ -n "$backup" ]]; then
       read 'answer?Restore this backup, keeping later edits? Type yes: '
       if [[ "$answer" == yes ]]; then python3 makeover.py undo --backup "$backup"; fi
     fi ;;
  4) open wallpaper/index.html ;;
  5) open -t docs/SETUP.md ;;
  *) print 'No changes made.' ;;
esac
read 'answer?Press Return to close. '
