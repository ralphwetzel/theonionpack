param(
  # Our preferred encoding
  [parameter(Mandatory)]
  [string]$File,

  [parameter(Mandatory)]
  [string]$Section,

  [parameter(Mandatory)]
  [string]$Value
)

Function Parse-IniFile ($file) {
  $ini = @{}

  # Create a default section if none exist in the file. Like a java prop file.
  $section = "NO_SECTION"
  $ini[$section] = @{}

  switch -regex -file $file {
    "^\[(.+)\]$" {
      $section = $matches[1].Trim()
      $ini[$section] = @{}
    }
    "^\s*([^#].+?)\s*=\s*(.*)" {
      $name,$value = $matches[1..2]
      # skip comments that start with semicolon:
      if (!($name.StartsWith(";"))) {
        $ini[$section][$name] = $value.Trim()
      }
    }
  }
  $ini
}

$ini = Parse-IniFile($File)

if ($ini.ContainsKey($Section)) {
  if ($ini[$Section].ContainsKey($Value)) {
    $r = $ini[$Section][$Value]
    Write-Host "${File}: [${Section}]${Value} = ${r}"
    return $r
  } else {
    Write-Host "Value '${Value}' not found in section '${Section}'."
  }
} else {
  Write-Host "Section '${Section}' not found in '${File}'."
}

# Signal error here!
$host.SetShouldExit(1)
exit 1
