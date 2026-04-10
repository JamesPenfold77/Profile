'macro OnbtnRunReportClick
'================================================================================
' Notable Personnel Audit Report
'
' Step 1 - GetNotablePatientFilenums
'   Runs the stored query "Notable Patients - Filenum List" which writes one
'   tab-delimited row per Notable patient (first field = filenum) to a temp
'   file.  No COM patient loading occurs here.
'
' Step 2 - BuildAuditReport
'   Reads the temp file, then for each filenum:
'     - Loads the patient via Profile.LoadPatientByFilenum
'     - Skips test patients (surname = "Test" or "Mouse", case-insensitive)
'     - Loads the patient audit log via ISPatientAuditFilter
'     - For each audit entry:
'         * AuditType must be EMR (1) or Demographic/Patient (3)
'         * Started date must fall within [DateStart, DateEnd]
'         * AccessedBy provider must NOT be a member of group PROVFRP
'       If all conditions pass, writes a tab-delimited line to the report.
'
' Report columns (as per spec):
'   Patient (NHI) | Patient Service (Label) | Patient DHC (POS)
'   Provider Name | Provider Role | POS (provider POS)
'   Access Date (dd/mm/yyyy) | Access Time (hh:mm:ss)
'   EMR Accessed (Yes/No) | Demographic Details Accessed (Yes/No)
'   Encounter Created? (Yes/No)
'
' Audit type constants (TSTypeOfAudit from IHProfBL_TLB):
'   0 = Unknown
'   1 = EMR  (clinical record access)
'   2 = Case
'   3 = Patient/Payer (demographic record access)
'
' Sources:
'   Profile/Common/Infrastructure/Scripting/USLogAuditFilter.pas
'   Profile/Common/Infrastructure/Scripting/USPatientOrCaseAudit.pas
'   Profile/Common/Infrastructure/Scripting/USAuditUtils.pas
'   Profile/Common/Infrastructure/Scripting/USProviderGroups.pas
'================================================================================

Option Explicit

' Module-level shared objects
Dim FSO
Dim aRept
Dim aNotableFileName

'==============================================================================
' ENTRY POINT
'==============================================================================
Sub Main()
  Set FSO   = CreateObject("Scripting.FileSystemObject")
  Set aRept = CreateOutputWindow

  ' Collect date range inputs from form controls
  Dim aDateStart
  Dim aDateEnd
  aDateStart = CDate(Controls_("dtpStartDate").Text)
  aDateEnd   = CDate(Controls_("dtpEndDate").Text)

  ' Step 1: Run stored query -> temp file of Notable patient filenums
  aNotableFileName = ""
  Call GetNotablePatientFilenums(aNotableFileName)

  If aNotableFileName = "" Then
    aRept.AddText "ERROR: Could not create Notable patients temp file."
    Exit Sub
  End If

  If Not FSO.FileExists(aNotableFileName) Then
    aRept.AddText "No Notable patients returned by stored query."
    Exit Sub
  End If

  ' Step 2: Walk the filenum list and build the audit report
  Call BuildAuditReport(aNotableFileName, aDateStart, aDateEnd, "PROVFRP")

  ' Cleanup temp file
  If FSO.FileExists(aNotableFileName) Then FSO.DeleteFile aNotableFileName, True
End Sub

'==============================================================================
' STEP 1 - GetNotablePatientFilenums
' Runs the stored query and writes results to a temp file.
' Sets aFileName to "" on failure.
'==============================================================================
Sub GetNotablePatientFilenums(ByRef aFileName)
  Dim cTempFolder
  cTempFolder = FSO.GetSpecialFolder(2)   ' 2 = system temp folder
  aFileName   = cTempFolder & "\" & FSO.GetTempName

  If FSO.FileExists(aFileName) Then FSO.DeleteFile aFileName, True

  ' Load the stored query by name
  On Error Resume Next
  Dim aLoader
  Set aLoader = Profile.MakeFindObjectQueriesLoader()
  aLoader.Name = "Notable Patients - Filenum List"

  Dim aQueryList
  Set aQueryList = aLoader.Load

  If Err.Number <> 0 Then
    aRept.AddText "ERROR loading stored query: " & Err.Description
    Err.Clear
    On Error GoTo 0
    aFileName = ""
    Exit Sub
  End If
  On Error GoTo 0

  If aQueryList.Count = 0 Then
    aRept.AddText "ERROR: Stored query 'Notable Patients - Filenum List' not found."
    aFileName = ""
    Exit Sub
  End If

  ' Configure run parameters: output to temp file, no row limit
  Dim aRunParam
  Set aRunParam = CreateFindObjectQueryRunParam
  aRunParam.RowCountLimit  = 10000000
  aRunParam.OutputFileName = aFileName
  aRunParam.IsAppendFile   = False

  Dim aQuery
  Set aQuery = aQueryList.Item(0)

  On Error Resume Next
  aQuery.Run(aRunParam)
  If Err.Number <> 0 Then
    aRept.AddText "ERROR running stored query: " & Err.Description
    Err.Clear
    On Error GoTo 0
    aFileName = ""
  End If
  On Error GoTo 0
End Sub

'==============================================================================
' STEP 2 - BuildAuditReport
' Reads Notable filenums from temp file, loads each patient and their audit
' log, applies all filter conditions, and writes matching rows to the report.
'
' Parameters:
'   aPatientListFile  - path to temp file from Step 1
'   aDateStart        - report start date (date only, no time)
'   aDateEnd          - report end date   (date only, no time)
'   aExcludeGroupCode - provider group code whose members are excluded
'==============================================================================
Sub BuildAuditReport(aPatientListFile, aDateStart, aDateEnd, aExcludeGroupCode)

  ' ---- Pre-load the excluded provider group (ISProviderGroup) ----
  ' Load once here for efficient ContainsPPPU calls inside the loop.
  Dim aExcludeGroup
  Set aExcludeGroup = Nothing

  Dim aGrpFilter
  Set aGrpFilter = Profile.CreateProviderGroupFilter
  aGrpFilter.Code = aExcludeGroupCode

  Dim aGroups
  Set aGroups = Profile.LoadProviderGroups(aGrpFilter)
  If aGroups.Count > 0 Then
    Set aExcludeGroup = aGroups.Items(0)   ' ISProviderGroup  (Items not Item)
  End If

  ' ---- Report header row ----
  aRept.AddText Join(Array( _
    "Patient", _
    "Patient Service", _
    "Patient DHC", _
    "Provider Name", _
    "Provider Role", _
    "POS", _
    "Access Date", _
    "Access Time", _
    "EMR Accessed", _
    "Demographic Details Accessed", _
    "Encounter Created?"), vbTab)

  ' ---- Provider info cache: key=PPPUID, value=tab-delimited "FullName|Role|POS" ----
  Dim aProviderCache
  Set aProviderCache = CreateObject("Scripting.Dictionary")

  ' ---- Open temp file and iterate one filenum per line ----
  Dim aFileStream
  Set aFileStream = FSO.OpenTextFile(aPatientListFile, 1, False)  ' 1=ForReading

  Do While Not aFileStream.AtEndOfStream
    Dim aLine
    aLine = Trim(aFileStream.ReadLine)

    ' Skip blank lines; skip header rows (non-numeric first character)
    Dim bSkipLine
    bSkipLine = False
    If aLine = "" Then bSkipLine = True
    If Not bSkipLine Then
      If Not IsNumeric(Left(aLine, 1)) Then bSkipLine = True
    End If

    If Not bSkipLine Then
      ' First tab-delimited field is the filenum
      Dim aLineFields
      aLineFields = Split(aLine, vbTab)
      Dim aFileNum
      aFileNum = 0
      On Error Resume Next
      aFileNum = CInt(Trim(aLineFields(0)))
      On Error GoTo 0

      If aFileNum > 0 Then
        Call ProcessPatient(aFileNum, aDateStart, aDateEnd, aExcludeGroup, aProviderCache)
      End If
    End If
  Loop  'ReadLine

  aFileStream.Close
End Sub

'==============================================================================
' ProcessPatient
' Loads one patient by filenum, applies test-patient filter, then iterates
' their audit log and calls WriteReportLine for qualifying entries.
'==============================================================================
Sub ProcessPatient(aFileNum, aDateStart, aDateEnd, aExcludeGroup, aProviderCache)

  ' ---- Load patient via LoadPatientByFilenum ----
  Dim aPatient   ' ISPatient
  Set aPatient = Nothing

  On Error Resume Next
  Set aPatient = Profile.LoadPatientByFilenum(aFileNum)
  If Err.Number <> 0 Then
    aRept.AddText "WARN: Could not load patient filenum " & CStr(aFileNum) & ": " & Err.Description
    Err.Clear
    On Error GoTo 0
    Exit Sub
  End If
  On Error GoTo 0

  If aPatient Is Nothing Then Exit Sub

  ' ---- Filter: skip test patients (surname = Test or Mouse) ----
  Dim aSurname
  aSurname = ""
  On Error Resume Next
  aSurname = aPatient.Surname
  On Error GoTo 0

  Dim bIsTestPatient
  bIsTestPatient = False
  If UCase(Trim(aSurname)) = "TEST"  Then bIsTestPatient = True
  If UCase(Trim(aSurname)) = "MOUSE" Then bIsTestPatient = True
  If bIsTestPatient Then Exit Sub

  ' ---- Load patient demographics for report columns ----
  Dim aNHI
  Dim aLabelName
  Dim aPatientPOS
  aNHI       = ""
  aLabelName = ""
  aPatientPOS = ""

  On Error Resume Next
  aNHI        = aPatient.NationalNum        ' NHI number
  aLabelName  = aPatient.LabelName          ' Patient Label Name
  aPatientPOS = aPatient.POS.Code           ' Patient POS code
  On Error GoTo 0

  ' ---- Build ISPatientAuditFilter for this patient ----
  ' Filter by PatientID; date range pre-filters are set to the report window.
  ' MaxCount = 0 means no server-side row cap.
  Dim aAuditFilter   ' ISPatientAuditFilter
  Set aAuditFilter = Profile.MakePatientAuditFilter
  aAuditFilter.PatientID = aPatient.ID
  aAuditFilter.StartDate = aDateStart
  aAuditFilter.EndDate   = aDateEnd + 1    ' EndDate is exclusive on the server
  aAuditFilter.MaxCount  = 0

  ' Load the audit collection (ISCollection of ISPatientOrCaseAudit)
  Dim aAuditLog   ' ISCollection
  Set aAuditLog = Nothing

  On Error Resume Next
  Set aAuditLog = aAuditFilter.Load
  If Err.Number <> 0 Then
    aRept.AddText "WARN: Could not load audit log for filenum " & CStr(aFileNum) & ": " & Err.Description
    Err.Clear
    On Error GoTo 0
    Exit Sub
  End If
  On Error GoTo 0

  If aAuditLog Is Nothing Then Exit Sub
  If aAuditLog.Count = 0  Then Exit Sub

  ' ---- Iterate audit entries ----
  Dim i
  For i = 0 To aAuditLog.Count - 1
    Dim aEntry   ' ISPatientOrCaseAudit
    Set aEntry = aAuditLog.Item(i)

    ' Condition 1: AuditType must be EMR (1) or Demographic/Patient (3)
    Dim aAuditType
    aAuditType = 0
    On Error Resume Next
    aAuditType = aEntry.AuditType
    On Error GoTo 0

    Dim bIsClinical
    Dim bIsDemographic
    bIsClinical    = (aAuditType = 1)   ' TSTypeOfAudit: 1 = EMR
    bIsDemographic = (aAuditType = 3)   ' TSTypeOfAudit: 3 = Patient/Payer

    If bIsClinical Or bIsDemographic Then

      ' Condition 2: Access date within report range
      ' (Server filter already pre-filters by StartDate/EndDate, but we
      ' validate here in case of timezone edge cases.)
      Dim aStarted
      aStarted = 0
      On Error Resume Next
      aStarted = aEntry.Started
      On Error GoTo 0

      Dim aAccessDate
      aAccessDate = Int(aStarted)   ' strip time component

      Dim bInRange
      bInRange = (aAccessDate >= Int(aDateStart)) And (aAccessDate <= Int(aDateEnd))

      If bInRange Then

        ' Condition 3: Provider NOT in excluded group
        Dim aAccessedBy
        aAccessedBy = 0
        On Error Resume Next
        aAccessedBy = aEntry.AccessedBy   ' PPPUID of the accessing provider
        On Error GoTo 0

        Dim bExcluded
        bExcluded = False
        If Not (aExcludeGroup Is Nothing) Then
          If aAccessedBy > 0 Then
            On Error Resume Next
            bExcluded = aExcludeGroup.ContainsPPPU(aAccessedBy)
            If Err.Number <> 0 Then
              bExcluded = False
              Err.Clear
            End If
            On Error GoTo 0
          End If
        End If

        If Not bExcluded Then
          ' All conditions met - write the report line
          Call WriteReportLine( _
            aEntry, _
            aNHI, aLabelName, aPatientPOS, _
            aAccessedBy, aAuditType, aStarted, _
            aProviderCache)
        End If

      End If   ' bInRange
    End If   ' bIsClinical Or bIsDemographic

  Next  'i
End Sub

'==============================================================================
' WriteReportLine
' Resolves provider details (with caching), formats all columns, and writes
' one tab-delimited line to the report output window.
'==============================================================================
Sub WriteReportLine(aEntry, _
                    aNHI, aLabelName, aPatientPOS, _
                    aAccessedBy, aAuditType, aStarted, _
                    aProviderCache)

  ' ---- Resolve provider info (cached by PPPUID) ----
  Dim cProviderKey
  cProviderKey = CStr(aAccessedBy)

  Dim cProvFullName
  Dim cProvRole
  Dim cProvPOS
  cProvFullName = ""
  cProvRole     = ""
  cProvPOS      = ""

  If aProviderCache.Exists(cProviderKey) Then
    ' Cache hit: unpack the stored "FullName|Role|POS" string
    Dim aCached
    aCached       = Split(aProviderCache(cProviderKey), "|")
    cProvFullName = aCached(0)
    cProvRole     = aCached(1)
    cProvPOS      = aCached(2)
  Else
    ' Cache miss: load provider from Profile
    If aAccessedBy > 0 Then
      On Error Resume Next
      Dim aProvider   ' ISProvider
      Set aProvider = Profile.LoadProvider(aAccessedBy)
      If Err.Number = 0 And Not (aProvider Is Nothing) Then
        cProvFullName = aProvider.FullName
        cProvRole     = aProvider.Role
        On Error Resume Next
        cProvPOS      = aProvider.POS.Code
        On Error GoTo 0
      End If
      If Err.Number <> 0 Then Err.Clear
      On Error GoTo 0
    End If
    ' Store in cache (pipe-delimited to avoid tab conflicts)
    aProviderCache.Add cProviderKey, cProvFullName & "|" & cProvRole & "|" & cProvPOS
  End If

  ' ---- Format access date and time ----
  Dim cAccessDate
  Dim cAccessTime
  cAccessDate = FormatDateTime(aStarted, 2)   ' 2 = vbShortDate (dd/mm/yyyy)
  cAccessTime = FormatTimeHMS(aStarted)       ' hh:mm:ss

  ' ---- Derive Yes/No columns from AuditType ----
  ' EMR Accessed:                 Yes when AuditType = 1 (EMR)
  ' Demographic Details Accessed: Yes when AuditType = 3 (Patient/Payer)
  ' Encounter Created:            Yes when AuditType = 1 (EMR creates encounter context)
  Dim cEMRAccessed
  Dim cDemoAccessed
  Dim cEncounterCreated

  If aAuditType = 1 Then
    cEMRAccessed      = "Yes"
    cDemoAccessed     = "No"
    cEncounterCreated = "Yes"
  Else
    cEMRAccessed      = "No"
    cDemoAccessed     = "Yes"
    cEncounterCreated = "No"
  End If

  ' ---- Write the tab-delimited report line ----
  aRept.AddText Join(Array( _
    aNHI, _
    aLabelName, _
    aPatientPOS, _
    cProvFullName, _
    cProvRole, _
    cProvPOS, _
    cAccessDate, _
    cAccessTime, _
    cEMRAccessed, _
    cDemoAccessed, _
    cEncounterCreated), vbTab)
End Sub

'==============================================================================
' HELPER FUNCTIONS
'==============================================================================

' PadTwo: zero-pads a single-digit integer to two characters.
Function PadTwo(n)
  If n < 10 Then
    PadTwo = "0" & CStr(n)
  Else
    PadTwo = CStr(n)
  End If
End Function

' FormatTimeHMS: extracts hh:mm:ss from a DateTime value.
' Format() is NOT available in the Profile VB scripting environment.
Function FormatTimeHMS(aDateTime)
  Dim aTotalSecs
  aTotalSecs = CInt(Int(((aDateTime - Int(aDateTime)) * 86400) + 0.5))
  Dim aHH
  Dim aMM
  Dim aSS
  aHH = aTotalSecs \ 3600
  aMM = (aTotalSecs Mod 3600) \ 60
  aSS = aTotalSecs Mod 60
  FormatTimeHMS = PadTwo(aHH) & ":" & PadTwo(aMM) & ":" & PadTwo(aSS)
End Function
