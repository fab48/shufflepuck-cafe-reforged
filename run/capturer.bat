@echo off
rem ============================================================
rem  Shufflepuck Cafe (Atari ST, Loriciel/Broderbund, 1989, v1.0)
rem  Lancement Hatari AVEC ENREGISTREMENT VIDEO
rem  BMP non compresse : aucun calcul a l enregistrement.
rem  25 images par seconde suffisent, et divisent le debit par deux.
rem  Chaque trame est ecrite en BMP dans work\captures\partie.avi
rem
rem  Images copiees sous des noms sans ambiguite dans work\disks\ :
rem    disk1.stx = amorcage, protegee (piste 79, 70 secteurs fantomes)
rem    disk2.stx = donnees, non protegee
rem  Les originaux restent dans le dossier d'archive, intacts.
rem
rem  Le lecteur B reste VIDE : Hatari refuse la meme image dans
rem  deux lecteurs ("cannot insert in the same drive").
rem  Le jeu reclame la disquette 2 DANS LE LECTEUR A :
rem    F12 -> Floppy disks -> Drive A: -> Browse -> disk2.stx
rem ============================================================

rem  Les captures Alt+G atterrissent dans le repertoire courant
cd /d D:\projets\shufflepuck\work\captures

set HATARI=D:\hatari\hatari-1.8.0_windows\hatari.exe
set TOS=D:\hatari\TOS\tos162fr.img
set DISKDIR=D:\projets\shufflepuck\work\disks

"%HATARI%" ^
  --machine ste ^
  --tos "%TOS%" ^
  --alert-level fatal ^
  --confirm-quit no ^
  --memsize 1 ^
  --cpuclock 8 ^
  --compatible on ^
  --blitter off ^
  --timer-d off ^
  --fast-boot off ^
  --fastfdc off ^
  --protect-floppy auto ^
  --disk-a "%DISKDIR%\disk1.stx" ^
  --zoom 2 ^
  --borders off ^
  --statusbar on ^
  --sound 44100 ^
  --ym-mixing model ^
  --window ^
  --avirecord ^
  --avi-vcodec bmp ^
  --avi-fps 25 ^
  --avi-file D:\projets\shufflepuck\work\captures\partie.avi ^
  --grab ^
  %*
