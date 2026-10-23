# Mac disk-image inventory (2026-10-22)

The nine Downloads images below were copied and verified on MiSTers `10.0.2.192` and `10.0.2.14` in:

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
| `AUX_3_1_1GB.hda` | 1,048,576,000 | `AUX_3_1_1GB_Use_In_Shoebill.zip` |

The A/UX ZIP member is `AUX_3_1_1GB.dsk`; its raw bytes were preserved and the extension changed to `.hda` for the core's file selector. The color MacAtrium archive came from `~/Downloads/mame0283-arm64/`; the other archives were directly in Downloads. `TestImages/QuadSquad8.hda` is the Downloads archive's image, separate from the active `games/MacQuadra800/QuadSquad8.hda` on `.192`.

## Verification

The [verification manifest](perf/shutdown_20261022/mac-image-copies.json) records source archive hashes, raw image hashes, byte sizes, and results for both hosts. Each source archive was SHA-256 checked and extracted with ZIP CRC checking on the Ubuntu build host. Each receiver checked the byte count and SHA-256 while writing a temporary file, read the file back to check SHA-256 again, and renamed it to the final filename only after those checks passed. The receiver refuses to overwrite an existing different file.

The hashes record delivery before guest use. The A/UX copy on `.192` was subsequently booted as writable test media; its [boot and shutdown results](aux-testing.md) are recorded separately. Boot and compatibility checks of the other newly copied images remain pending. The `.14` Dorado session was left running throughout.

## A/UX image supplied after the initial search

The user subsequently found `~/Downloads/AUX_3_1_1GB_Use_In_Shoebill.zip`. It was copied to both MiSTers and used for the A/UX regression on `.192` with 32 MB RAM. The [verification record](perf/aux_20261022/image-verification.json) preserves the source archive and pre-boot image hashes.

Staging archives and the copy logs are retained at `misterubuntu:~/mister/q800_images_20261022/` and `~/mister/q800_aux_20261022/`. Disk images are not stored in Git.
