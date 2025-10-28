on run argv
  if (count of argv) < 3 then
    display dialog "Usage: osascript push_to_notes.scpt <Note Title> <Folder Name> <file1> [file2] ..." buttons {"OK"} default button 1
    return
  end if

  set theTitle to item 1 of argv
  set theFolder to item 2 of argv
  set theFiles to items 3 thru -1 of argv

  tell application "Notes"
    -- ensure folder exists
    set targetFolder to missing value
    repeat with f in folders
      if name of f is theFolder then
        set targetFolder to f
        exit repeat
      end if
    end repeat
    if targetFolder is missing value then
      set targetFolder to make new folder with properties {name:theFolder}
    end if

    -- find or create note
    set targetNote to missing value
    repeat with n in notes of targetFolder
      if name of n is theTitle then
        set targetNote to n
        exit repeat
      end if
    end repeat
    if targetNote is missing value then
      set targetNote to make new note at targetFolder with properties {name:theTitle, body:""}
    end if

    -- append file contents
    repeat with p in theFiles
      set fp to (POSIX file (p as string)) as alias
      set fconts to read fp as «class utf8»
      set body of targetNote to (body of targetNote) & return & return & fconts
    end repeat
    activate
  end tell
end run
