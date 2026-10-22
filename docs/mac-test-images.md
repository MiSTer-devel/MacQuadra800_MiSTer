# Mac disk-image inventory (2026-10-22)

The eight Downloads images below are mirrored on MiSTers `10.0.2.192` and `10.0.2.14` in:

```text
/media/fat/games/MacQuadra800/TestImages/
```

| Image | Bytes | Source archive in `~/Downloads` |
|---|---:|---|
| `QuadSquad8.hda` | 2,146,461,696 | `QuadSquad8.hda.zip` |
| `MacQuadra800_Problem_Games.hda` | 524,337,152 | `MacQuadra800_Previous_Problem_Games_working_now.hda.zip` |
| `Mac68KColorGames_v1.hda` | 786,473,472 | `Mac68KColorGames_v1.hda.zip` |
| `HD00_512 MacII_HDD-expanded.hda` | 2,146,462,208 | `HD00_512 MacII_HDD-expanded.hda.zip` |
| `MacAtrium-final-bw-608.hda` | 1,363,173,376 | `MacAtrium-final-bw-608.hda.zip` |
| `MacAtrium-final-color-71.hda` | 2,044,750,336 | `MacAtrium-final-color-71.hda.zip` |
| `mac os 7.01 us.vhd` | 21,411,840 | `mac os 7.01 us.vhd.zip` |
| `With-Benchmarking-and-CDROM.hda.vhd` | 21,037,056 | `With-Benchmarking-and-CDROM.hda.zip` |

The color MacAtrium archive came from `~/Downloads/mame0283-arm64/`; the other archives were directly in Downloads. `TestImages/QuadSquad8.hda` is the Downloads archive's image, separate from the active `games/MacQuadra800/QuadSquad8.hda` on `.192`.

## Verification

The [verification manifest](perf/shutdown_20261022/mac-image-copies.json) records source archive hashes, raw image hashes, byte sizes, and results for both hosts. Each source archive was SHA-256 checked and extracted with ZIP CRC checking on the Ubuntu build host. Each receiver checked the byte count and SHA-256 while writing a temporary file, read the file back to check SHA-256 again, and renamed it to the final filename only after those checks passed. The receiver refuses to overwrite an existing different file.

The copy results establish data integrity; boot and compatibility checks of these newly copied images remain pending. No mounted guest image, core selection, or guest configuration was changed by distribution. The `.14` Dorado session was left running; `.192` was left at the Macintosh safe-to-switch-off screen after the [shutdown qualification](shutdown-testing.md).

## Missing A/UX image

No image named for A/UX or `HD60_512-AUX3.1-Installed.hda`, or its expected backup ZIP, was found in the searches of either MiSTer's `/media/fat`, local Downloads (including ZIP member names), or the build host's `/home/alans`. A/UX 3.1 boot and shutdown remain unqualified; the regression needs the installed image and the OSD RAM setting at 32 MB.

Staging archives and the copy log are retained at `misterubuntu:~/mister/q800_images_20261022/`. Disk images are not stored in Git.
