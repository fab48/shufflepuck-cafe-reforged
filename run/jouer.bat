@echo off
rem ============================================================
rem  Shufflepuck Cafe (Atari ST, Loriciel/Broderbund, 1989, v1.0)
rem  Lancement Hatari
rem
rem  Images copiees sous des noms sans ambiguite dans work\disks\ :
rem    disk1.stx = amorcage, protegee (piste 79, 70 secteurs fantomes)
rem    disk2.stx = donnees, non protegee
rem  Les originaux restent dans le dossier d'archive, intacts.
rem
rem  Le jeu reclame la disquette 2 DANS LE LECTEUR A :
rem    F12 -> Floppy disks -> Drive A: -> Browse -> disk2.stx
rem ============================================================

set HATARI=D:\hatari\hatari-1.8.0_windows\hatari.exe
set TOS=D:\hatari\TOS\tos162fr.img
set DISKDIR=D:\projets\shufflepuck\work\disks

"%HATARI%" ^
  --machine st ^
  --tos "%TOS%" ^
  --memsize 1 ^
  --cpuclock 8 ^
  --compatible on ^
  --blitter off ^
  --timer-d off ^
  --fast-boot off ^
  --fastfdc off ^
  --protect-floppy auto ^
  --disk-a "%DISKDIR%\disk1.stx" ^
  --disk-b "%DISKDIR%\disk2.stx" ^
  --zoom 2 ^
  --borders off ^
  --statusbar on ^
  --sound 44100 ^
  --ym-mixing model ^
  --window ^
  %*
