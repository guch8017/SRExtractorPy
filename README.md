# SRExtractorPy
A data extractor for a certain anime game.

# Usage

### 1. Preparation
We need to prepare two things before using this program.

1. Class dump file `dump.cs` and `stringLiteral.json` from [Il2CppDumper](https://github.com/Perfare/Il2CppDumper). You may need to decrypt the binary file before using Il2CppDumper.
2. Baked excel files stored in `$GameRootDir\XXXXXXXX_Data\Persistent\DesignData\Windows`. You can launch the game to let the game download it for you or use the [download script](/tools/design_data_downloader.py) (However you still need to get the url by requesting the dispatch server...)

### 2. Get ExcelClass - ExcelName mapping
We need to get the excel file name to map the binary data to class fields. A (script)[/tools/guess_config_name.py] is provided to find out the relationship automatically, but it sometimes provide wrong results. You may use your own way to build the mapping.

### 3. Extract excels and configs
Run command to extract things from the baked binary files.
```bash
python main.py \
  --design $PATH_TO_DESIGN_DATA_DIR \
  --cs $PATH_TO_DUMP.CS \
  --output $PATH_TO_OUTPUT_DIR \
  --excel-map $PATH_TO_EXCEL_CLASS_MAPPING_JSON \
  --version $GAME_VERSION \  # As the design index format change in 1.2.53, we need to specify the game version
  --beta  # Beta and release version has different dynamic value format, if you are trying to extract a beta version file, add this line.
```

# Credits

* [Il2CppDumper](https://github.com/Perfare/Il2CppDumper)
* [frida-il2cpp-bridge](https://github.com/vfsfitvnm/frida-il2cpp-bridge)
* Metadata by @Razmoth
* Special thanks to helps from Creperie
