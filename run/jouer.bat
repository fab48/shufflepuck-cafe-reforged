@echo off
rem ============================================================
rem  Shufflepuck Cafe (Atari ST, Loriciel/Broderbund, 1989)
rem  Lancement Hatari - configuration STF d'epoque
rem
rem  ATTENTION aux noms courts 8.3 : l'ordre est INVERSE
rem    SHUFFL~2.STX = disquette 1 (boot, protegee piste 79)
rem    SHUFFL~1.STX = disquette 2 (donnees, non protegee)
rem ============================================================

set HATARI=D:\hatari\hatari-1.8.0_windows\hatari.exe
set TOS=D:\hatari\TOS\tos162fr.img
set DISK1=C:\SHUFFL~1\SHUFFL~2.STX
set DISK2=C:\SHUFFL~1\SHUFFL~1.STX

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
  --disk-a "%DISK1%" ^
  --disk-b "%DISK2%" ^
  --zoom 2 ^
  --borders off ^
  --statusbar on ^
  --sound 44100 ^
  --ym-mixing model ^
  --window ^
  %*
