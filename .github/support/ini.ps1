#####
# PowerShell Script to read  value from an .ini-style script
# using code from https://stackoverflow.com/questions/417798/ini-file-parsing-in-powershell
# Example: .github\support\ini.ps1 -File theonionpack\setup.ini -Section obfs4 -Value version
# -File: path to .ini - file
# -Section: name of the section to read from
# -Value: name of the parameter to retrieve
#
# returns the value if found; if not, exits with exit code 1

param(

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
