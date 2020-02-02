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

Write-Host $File
$ini = Parse-IniFile($File)

Write-Host $Section
Write-Host $Value

Write-Host $ini[$Section][$Value]

if ($ini.ContainsKey($Section)) {
  if ($ini[$Section] -contains $Value) {
    return $ini[$Section][$Value]
  } else {
    Write-Host "${Value} not found in section ${Section}."
  }
} else {
  Write-Host "Section ${Section} not found in ${File}."
}
