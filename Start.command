#!/bin/zsh
set -u
cd -- "${0:A:h}" || exit 1
print 'Neon Horizon — Mac Makeover'
print '1  Preview the complete preset (changes nothing)'
print '2  Apply the complete preset, including 7-day clipboard history and Option Hot Corners'
print '3  Undo a previous preset run'
print '4  Preview the default Sakura Park wallpaper'
print '5  Open the setup guide'
print '6  Preview a personalized Dock layout'
print '7  Apply the personalized Dock layout'
print '8  Undo a personalized Dock layout'
read -r 'choice?Choose 1–8 [1]: ' || exit 0
case "${choice:-1}" in
  1|2|3|6|7|8)
    if ! command -v python3 >/dev/null 2>&1; then
      print 'Python 3 is needed for the optional setup tool. Options 4 and 5 work without it.'
      print 'Download Python from https://www.python.org/downloads/macos/ or use docs/SETUP.md.'
      read -r 'answer?Press Return to close. '
      exit 1
    fi ;;
esac
case "${choice:-1}" in
  1) python3 makeover.py plan --groups all ;;
  2) python3 makeover.py apply --groups all --confirm ;;
  3) python3 makeover.py backups && {
     read -r 'backup?Paste the full backup path above, or Return to cancel: '
     if [[ -n "$backup" ]]; then
       read -r 'answer?Restore this backup, keeping later edits? Type yes: '
       if [[ "$answer" == yes ]]; then python3 makeover.py undo --backup "$backup"; fi
     fi
     } ;;
  4) open wallpaper/sakura-park.png ;;
  5) open -t docs/SETUP.md ;;
  6) python3 dock.py plan ;;
  7) python3 dock.py apply --confirm ;;
  8) python3 dock.py backups && {
     read -r 'backup?Paste the full Dock backup path above, or Return to cancel: '
     if [[ -n "$backup" ]]; then
       read -r 'answer?Restore this layout if it has no later edits? Type yes: '
       if [[ "$answer" == yes ]]; then python3 dock.py undo --backup "$backup"; fi
     fi
     } ;;
  *) print 'No changes made.' ;;
esac
result=$?
read -r 'answer?Press Return to close. '
exit "$result"
