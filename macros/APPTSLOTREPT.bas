' -----------------------------------------------------------------------
' APPTSLOTREPT
' Description: The Slot Availability Report macro generates a list of
' appointment slots for a specified date range, filtered by provider
' group, location (POS), and appointment type. Each slot is marked as
' Available, Booked, or Locked, giving practice managers a clear picture
' of scheduling capacity.
' The report is produced as a Profile Stored Report List, which can be
' viewed, sorted, and printed from within Profile.
' USAGE
' This library is used by the form Appointment Report
'      sApptRept = Profile.LoadShortCodeByCodeType("APPTSLOTREPT", 10).MacroText
'      executeGlobal sApptRept
' -----------------------------------------------------------------------

Dim aRept          ' module-level stored report
Dim aProgressBar   ' module-level progress bar (ISModalProcessDisplay)

' -----------------------------------------------------------------------
' Main — example entry point showing all parameters
' -----------------------------------------------------------------------
Sub Main()

  Dim aStartDate, aEndDate
  Dim aApptTypeCodes, aProvGrpCodes, aPosIDs, aApptDuration
  Dim bIncludeBooked

  aStartDate     = #01-APR-2026#
  aEndDate       = #30-APR-2026#
  aApptTypeCodes = "CONSULT"     ' comma-separated codes, or "" for all
  aProvGrpCodes  = "SPEC1"       ' comma-separated group codes, or "" for all
  aPosIDs        = "3"           ' comma-separated POS IDs, or "" for all
  aApptDuration  = ""            ' "<60 Mins", "60 to 90 Mins", "90 to 120 Mins",
                                 ' ">120 Mins", or "" for all durations
  bIncludeBooked = True

  Call GenerateSlotReport( _
      aStartDate, _
      aEndDate, _
      aApptTypeCodes, _
      aProvGrpCodes, _
      aPosIDs, _
      aApptDuration, _
      bIncludeBooked)
End Sub

' -----------------------------------------------------------------------
' PadTwo / FormatTime helpers
' -----------------------------------------------------------------------
Function PadTwo(n)
  If n < 10 Then
    PadTwo = "0" & CStr(n)
  Else
    PadTwo = CStr(n)
  End If
End Function

Function FormatTime(aTime)
  Dim aTotalMins
  aTotalMins = CInt(Int((aTime - Int(aTime)) * 1440 + 0.5))
  FormatTime = PadTwo(aTotalMins \ 60) & ":" & PadTwo(aTotalMins Mod 60)
End Function

' -----------------------------------------------------------------------
' DisplayProgressBar — creates or updates the progress bar.
' Call with aStep = 0 to initialise; subsequent calls advance the bar.
' aMax is the total number of steps (set on first call, ignored after).
' aCaption describes the current step shown to the user.
' -----------------------------------------------------------------------
Sub DisplayProgressBar(aStep, aCaption, aMax)
  If aStep = 0 Then
    Set aProgressBar = Profile.CreateModalProcessDisplay(False)
    aProgressBar.ProcessName = "Generating Appointment Slot Report"
    aProgressBar.MaxValue    = aMax
    aProgressBar.AllowCancel = True
  End If
  aProgressBar.Position = aStep
  aProgressBar.Caption  = "Step " & (aStep + 1) & " of " & aMax & ": " & aCaption
End Sub

' -----------------------------------------------------------------------
' GetDurationRange — converts an aApptDuration label into min/max minutes.
' Returns True if a filter is active; aMinMins and aMaxMins are set.
' Returns False if aApptDuration is "" (no filter — include all durations).
' -----------------------------------------------------------------------
Function GetDurationRange(aApptDuration, aMinMins, aMaxMins)
  GetDurationRange = True
  Select Case Trim(aApptDuration)
    Case "<60 Mins"
      aMinMins = 0
      aMaxMins = 59
    Case "60 to 90 Mins"
      aMinMins = 60
      aMaxMins = 90
    Case "90 to 120 Mins"
      aMinMins = 91
      aMaxMins = 120
    Case ">120 Mins"
      aMinMins = 121
      aMaxMins = 99999
    Case Else
      ' Empty string or unrecognised value — include all durations
      aMinMins = 0
      aMaxMins = 99999
      GetDurationRange = False
  End Select
End Function

' -----------------------------------------------------------------------
' CheckDayIsActive — VB reimplementation of _TBAppointmentRule.CheckDayIsActive
' Returns True if aRule fires on aDate (pure date value, no time component).
' Source: Profile/Common/Business/UBAppointmentRules.pas
' -----------------------------------------------------------------------
Function CheckDayIsActive(aRule, aDate)
  CheckDayIsActive = False
  Dim aDay
  aDay = Int(aDate)
  If Int(aRule.RuleStart) > aDay Then Exit Function
  If aRule.RuleFinish <> 0 And Int(aRule.RuleFinish) < aDay Then Exit Function

  Dim aCycleDay
  Dim aCycleType
  aCycleType = aRule.RuleCycleType

  If aCycleType = 5 Then        ' sarctOnce — active every day in validity window
    CheckDayIsActive = True
    Exit Function

  ElseIf aCycleType = 0 Then   ' sarctAbsolute
    Dim aMaxDayAbs
    If aRule.RulePeriod > 0 Then aMaxDayAbs = aRule.RulePeriod Else aMaxDayAbs = 1
    aCycleDay = (Int(aDay) - Int(aRule.RuleStart)) Mod aMaxDayAbs + 1

  ElseIf aCycleType = 1 Then   ' sarctWeekly
    Dim iWeek
    iWeek = Weekday(aRule.RuleStart) - 2
    If iWeek < 0 Then iWeek = iWeek + 7
    Dim aBaseWeek
    aBaseWeek = Int(aRule.RuleStart) - iWeek
    Dim aMaxDayWeek
    If aRule.RulePeriod > 0 Then
      aMaxDayWeek = aRule.RulePeriod + (6 - ((aRule.RulePeriod - 1) Mod 7))
    Else
      aMaxDayWeek = 7
    End If
    aCycleDay = (Int(aDay) - Int(aBaseWeek)) Mod aMaxDayWeek + 1

  ElseIf aCycleType = 2 Then   ' sarctWeekMonthly
    Dim aYear, aMonth, aDayNum
    aYear = Year(aDay) : aMonth = Month(aDay) : aDayNum = Day(aDay)
    Dim aMonthStart
    aMonthStart = DateSerial(aYear, aMonth, 1)
    Dim iWM
    iWM = Weekday(aMonthStart) - 1
    If iWM < 1 Then iWM = iWM + 7
    aCycleDay = ((aDayNum - 1) Mod 7) + iWM
    If aCycleDay > 7 Then aCycleDay = aCycleDay - 7
    aCycleDay = aCycleDay + ((aDayNum - 1) \ 7) * 7

  Else
    Exit Function
  End If

  Dim aDayCount
  aDayCount = aRule.RuleDayCount
  If aDayCount > 0 Then
    Dim j
    For j = 0 To aDayCount - 1
      If aRule.RuleDay(j) = aCycleDay Then
        CheckDayIsActive = True
        Exit Function
      End If
    Next  'j
  Else
    If aCycleDay = 1 Then CheckDayIsActive = True
  End If
End Function

' -----------------------------------------------------------------------
' CollectProviderCodes — recursively walks a provider group and all its
' nested child groups, collecting Provider.Code -> Provider.ID into
' aCodeDict. aVisitedIDs (Dictionary) prevents infinite loops from
' circular group references.
' Source: USProviderGroups.pas — ISProviderGroup.GroupMembers confirmed.
' -----------------------------------------------------------------------
Sub CollectProviderCodes(aGrpObj, aCodeDict, aVisitedIDs)
  Dim aGrpID
  aGrpID = CStr(aGrpObj.ID)
  If aVisitedIDs.Exists(aGrpID) Then Exit Sub
  aVisitedIDs.Add aGrpID, 1

  ' Add direct PPPU members by Code
  Dim aMembers
  Set aMembers = aGrpObj.PPPUMembers
  Dim m
  For m = 0 To aMembers.Count - 1
    Dim aMember
    Set aMember = aMembers.Item(m)
    Dim aCode
    aCode = aMember.Code
    If aCode <> "" And Not aCodeDict.Exists(aCode) Then
      aCodeDict.Add aCode, aMember.ID
    End If
  Next  'm

  ' Recurse into child groups
  Dim aChildGroups
  Set aChildGroups = aGrpObj.GroupMembers
  Dim g
  For g = 0 To aChildGroups.Count - 1
    CollectProviderCodes aChildGroups.Items(g), aCodeDict, aVisitedIDs
  Next  'g
End Sub

' -----------------------------------------------------------------------
' IsSlotBooked — returns booking status of a slot:
'   ""       = available (no overlapping appointment)
'   "Booked" = overlapping non-cancelled appointment with a patient
'   "Locked" = overlapping non-cancelled appointment with no patient
' aSlotStart and aSlotEnd must include the date portion (full DateTime).
' cEpsilon absorbs floating point drift from Duration / 1440 arithmetic,
' preventing adjacent slots from being falsely marked Booked.
' -----------------------------------------------------------------------
Function IsSlotBooked(aProviderID, aPosID, aDate, aSlotStart, aSlotEnd)
  IsSlotBooked = ""
  Dim cEpsilon
  cEpsilon = 0.5 / 1440   ' half a minute — absorbs /1440 floating point drift

  Dim aProvider
  Set aProvider = Profile.LoadProviderById(aProviderID)
  Dim aAppts
  Set aAppts = aProvider.LoadAppointments(aDate, "")
  Dim k
  For k = 0 To aAppts.Count - 1
    Dim aAppt
    Set aAppt = aAppts.Item(k)
    If aAppt.PosID = aPosID And Not aAppt.IsCancelled Then
      Dim aApptStart, aApptEnd
      aApptStart = aAppt.BookTime
      aApptEnd   = aAppt.BookTime + (aAppt.Duration / 1440)
      ' Epsilon prevents adjacent appointments (end == start) from falsely matching
      If aApptStart < (aSlotEnd - cEpsilon) And aApptEnd > (aSlotStart + cEpsilon) Then
        If aAppt.PatientId > 0 Then
          IsSlotBooked = "Booked"
        Else
          IsSlotBooked = "Locked"
        End If
        Exit Function
      End If
    End If
  Next  'k
End Function

' -----------------------------------------------------------------------
' GenerateSlotReport
'
' Parameters:
'   aStartDate      — report start date
'   aEndDate        — report end date
'   aApptTypeCodes  — comma-separated appt type short codes, "" = all
'   aProvGrpCodes   — comma-separated provider group codes, "" = all
'   aPosIDs         — comma-separated POS integer IDs, "" = all
'   aApptDuration   — duration band filter:
'                     "<60 Mins", "60 to 90 Mins", "90 to 120 Mins",
'                     ">120 Mins", or "" = all durations
'   bIncludeBooked  — True:  show all slots (available, booked, locked)
'                     False: show available slots only
' -----------------------------------------------------------------------
Sub GenerateSlotReport(aStartDate, aEndDate, aApptTypeCodes, aProvGrpCodes, aPosIDs, aApptDuration, bIncludeBooked)

  ' Progress bar has 4 major steps:
  '   0 — Resolving provider groups
  '   1 — Loading appointment rules
  '   2 — Processing rules (rule loop — longest step)
  '   3 — Saving and displaying report
  Dim cTotalSteps
  cTotalSteps = 4
  DisplayProgressBar 0, "Resolving provider groups", cTotalSteps

  ' --- Create stored report ---
  Set aRept = CreateStoredReportList("Available Slots")
  aRept.Caption = "Available Slots " & FormatDateTime(aStartDate, 2) & " to " & FormatDateTime(aEndDate, 2)

  ' Columns:
  '  0  RuleName  width=0   hidden
  '  1  Provider  width=150
  '  2  Date      width=80
  '  3  Start     width=50
  '  4  End       width=50
  '  5  Duration  width=50  integer
  '  6  POS       width=50
  '  7  ApptType  width=80
  '  8  Booked    width=50
  aRept.AddColumn "RuleName", 0,   0, True, 1
  aRept.AddColumn "Provider", 150, 0, True, 1
  aRept.AddColumn "Date",     80,  0, True, 1
  aRept.AddColumn "Start",    50,  0, True, 1
  aRept.AddColumn "End",      50,  0, True, 1
  aRept.AddColumn "Duration", 50,  1, True, 2
  aRept.AddColumn "POS",      50,  0, True, 1
  aRept.AddColumn "ApptType", 80,  0, True, 1
  aRept.AddColumn "Booked",   50,  0, True, 1

  ' --- Resolve duration filter to min/max minutes ---
  ' GetDurationRange returns False when aApptDuration is "" (no filter).
  Dim aDurMinMins, aDurMaxMins
  Dim bDurationFilter
  bDurationFilter = GetDurationRange(aApptDuration, aDurMinMins, aDurMaxMins)

  ' --- Build appointment type lookup dictionary ---
  Dim aApptTypeDict
  Set aApptTypeDict = CreateObject("Scripting.Dictionary")
  Dim aToken
  If aApptTypeCodes <> "" Then
    For Each aToken In Split(aApptTypeCodes, ",")
      aToken = Trim(aToken)
      If aToken <> "" And Not aApptTypeDict.Exists(aToken) Then
        aApptTypeDict.Add aToken, 1
      End If
    Next  'aToken
  End If

  ' --- Build POS ID lookup dictionary ---
  Dim aPosDict
  Set aPosDict = CreateObject("Scripting.Dictionary")
  If aPosIDs <> "" Then
    For Each aToken In Split(aPosIDs, ",")
      aToken = Trim(aToken)
      If aToken <> "" And Not aPosDict.Exists(aToken) Then
        aPosDict.Add aToken, 1
      End If
    Next  'aToken
  End If

  ' --- Resolve provider group codes to flat Provider.Code -> Provider.ID dict ---
  ' Groups are recursive: a group may contain sub-groups as well as providers.
  ' ContainsPPPU only tests direct membership, so we must walk GroupMembers
  ' recursively to collect all transitive provider members.
  Dim aProviderCodeDict
  Set aProviderCodeDict = CreateObject("Scripting.Dictionary")

  If aProvGrpCodes <> "" Then
    For Each aToken In Split(aProvGrpCodes, ",")
      aToken = Trim(aToken)
      If aToken <> "" Then
        Dim aGrpFilter
        Set aGrpFilter = Profile.CreateProviderGroupFilter
        aGrpFilter.Code = aToken
        Dim aGroups
        Set aGroups = Profile.LoadProviderGroups(aGrpFilter)
        If aGroups.Count > 0 Then
          Dim aVisited
          Set aVisited = CreateObject("Scripting.Dictionary")
          CollectProviderCodes aGroups.Items(0), aProviderCodeDict, aVisited
        End If
      End If
    Next  'aToken
  End If

  ' Check for cancel after provider group resolution
  If aProgressBar.Cancelled Then
    Profile.MsgBox "Report cancelled.", 64, "Slot Report"
    Exit Sub
  End If

  ' --- Step 1: Load appointment rules from server ---
  DisplayProgressBar 1, "Loading appointment rules", cTotalSteps

  ' --- Configure server-side rule filter ---
  Dim aFilter
  Set aFilter = Profile.CreateAppointmentRuleFilter
  aFilter.DateRangeKind = 3   ' sarfValidRange
  aFilter.StartDate = aStartDate
  aFilter.EndDate   = aEndDate

  ' Server-side POS filter
  If aPosIDs <> "" Then
    For Each aToken In Split(aPosIDs, ",")
      aToken = Trim(aToken)
      If aToken <> "" Then aFilter.POSes.Add CInt(aToken)
    Next  'aToken
  End If

  ' Server-side provider filter (from resolved group members)
  ' aProvCode = Provider.Code string (key); aProviderCodeDict(aProvCode) = Provider.ID integer (value)
  If aProviderCodeDict.Count > 0 Then
    Dim aProvCode
    For Each aProvCode In aProviderCodeDict.Keys
      aFilter.Providers.Add aProviderCodeDict(aProvCode)
    Next  'aProvCode
  End If

  Dim aRules
  Set aRules = aFilter.Load

  ' Check for cancel after rule load
  If aProgressBar.Cancelled Then
    Profile.MsgBox "Report cancelled.", 64, "Slot Report"
    Exit Sub
  End If

  ' --- Step 2: Process rules ---
  ' The progress bar MaxValue was set to cTotalSteps (4) at initialisation.
  ' For the rule loop we switch to rule-level granularity by updating the
  ' caption on each rule so the user can see which provider is being processed,
  ' while keeping Position advancing one tick per rule within step 2.
  ' We re-initialise the bar here with aRules.Count as the new MaxValue so
  ' the bar fills smoothly across the rule loop.
  Dim aRuleCount
  aRuleCount = aRules.Count

  Set aProgressBar = Profile.CreateModalProcessDisplay(False)
  aProgressBar.ProcessName = "Generating Appointment Slot Report"
  aProgressBar.MaxValue    = aRuleCount
  aProgressBar.AllowCancel = True
  aProgressBar.Position    = 0
  aProgressBar.Caption     = "Processing " & aRuleCount & " appointment rules..."

  ' --- Cache provider FullName per ProviderID to avoid repeated loads ---
  Dim aProvNameDict
  Set aProvNameDict = CreateObject("Scripting.Dictionary")

  Dim i
  Dim aRowNum
  aRowNum = -1

  For i = 0 To aRuleCount - 1

    ' Check for cancel at the start of each rule
    If aProgressBar.Cancelled Then
      Profile.MsgBox "Report cancelled after processing " & i & " of " & aRuleCount & " rules.", 64, "Slot Report"
      Exit Sub
    End If

    Dim aRule
    Set aRule = aRules.Item(i)

    ' Advance progress bar — show provider name if resolvable
    Dim sRuleCaption
    sRuleCaption = "Rule " & (i + 1) & " of " & aRuleCount
    If aRule.RuleType = 1 Then
      Dim sCaptionProvKey
      sCaptionProvKey = CStr(aRule.ProviderID)
      If aProvNameDict.Exists(sCaptionProvKey) Then
        sRuleCaption = sRuleCaption & ": " & aProvNameDict(sCaptionProvKey)
      End If
    End If
    aProgressBar.Position = i
    aProgressBar.Caption  = sRuleCaption

    If aRule.RuleType = 1 Then   ' sartPersonal only

      ' --- Duration filter ---
      ' Compare rule Duration (integer minutes) against the requested band.
      ' Skips the rule entirely if its duration falls outside the band,
      ' avoiding unnecessary date walking and slot expansion.
      Dim bDurationMatch
      bDurationMatch = True
      If bDurationFilter Then
        bDurationMatch = (aRule.Duration >= aDurMinMins And aRule.Duration <= aDurMaxMins)
      End If

      If bDurationMatch Then

        ' --- Appointment type filter ---
        Dim aTypeCode
        aTypeCode = ""
        On Error Resume Next
        aTypeCode = aRule.TypeCode.Code
        On Error GoTo 0

        Dim bTypeMatch
        bTypeMatch = True
        If aApptTypeDict.Count > 0 Then
          bTypeMatch = (aTypeCode <> "" And aApptTypeDict.Exists(aTypeCode))
        End If

        If bTypeMatch Then

          ' --- Provider group membership check ---
          ' Look up the rule's provider by Code in the pre-resolved flat dictionary.
          ' This correctly handles providers in nested sub-groups.
          Dim bProvGrpMatch
          bProvGrpMatch = True
          If aProviderCodeDict.Count > 0 Then
            Dim aRuleProvCode
            aRuleProvCode = ""
            On Error Resume Next
            aRuleProvCode = Profile.LoadProviderById(aRule.ProviderID).Code
            On Error GoTo 0
            bProvGrpMatch = (aRuleProvCode <> "" And aProviderCodeDict.Exists(aRuleProvCode))
          End If

          If bProvGrpMatch Then

            ' --- Resolve provider FullName (cached per ProviderID) ---
            Dim aProvKey
            aProvKey = CStr(aRule.ProviderID)
            Dim aProvFullName
            If aProvNameDict.Exists(aProvKey) Then
              aProvFullName = aProvNameDict(aProvKey)
            Else
              Dim aProvObj
              Set aProvObj = Profile.LoadProviderById(aRule.ProviderID)
              aProvFullName = aProvObj.FullName
              aProvNameDict.Add aProvKey, aProvFullName
            End If

            ' Update caption now that we have the provider name
            aProgressBar.Caption = "Rule " & (i + 1) & " of " & aRuleCount & ": " & aProvFullName

            ' --- Clamp date walk to intersection of report range and rule validity ---
            Dim aRuleFinish
            aRuleFinish = aRule.RuleFinish
            Dim aWalkStart, aWalkEnd
            aWalkStart = Int(aStartDate)
            If Int(aRule.RuleStart) > aWalkStart Then aWalkStart = Int(aRule.RuleStart)
            aWalkEnd = Int(aEndDate)
            If aRuleFinish <> 0 And Int(aRuleFinish) < aWalkEnd Then aWalkEnd = Int(aRuleFinish)

            Dim aDate
            aDate = aWalkStart

            Do While aDate <= aWalkEnd

              If CheckDayIsActive(aRule, aDate) Then

                ' Slot start carries the date portion so overlap comparison
                ' against appointment BookTime (full DateTime) is correct.
                Dim aSlotStart
                aSlotStart = Int(aDate) + (aRule.TimeStart - Int(aRule.TimeStart))

                Dim aSessionEnd
                aSessionEnd = Int(aDate) + (aRule.TimeFinish - Int(aRule.TimeFinish))

                Do While aSlotStart < aSessionEnd

                  Dim aSlotEnd
                  aSlotEnd = aSlotStart + (aRule.Duration / 1440)

                  ' Only emit complete slots that fit within the session
                  If aSlotEnd <= aSessionEnd + (1 / 1440) Then

                    Dim sBookedStatus
                    sBookedStatus = IsSlotBooked(aRule.ProviderID, aRule.PosID, aDate, aSlotStart, aSlotEnd)

                    If bIncludeBooked Or sBookedStatus = "" Then
                      aRept.AddRow
                      aRowNum = aRowNum + 1
                      aRept.Cells(aRowNum, 0).Value = aRule.RuleName
                      aRept.Cells(aRowNum, 1).Value = aProvFullName
                      aRept.Cells(aRowNum, 2).Value = FormatDateTime(aDate, 2)
                      aRept.Cells(aRowNum, 3).Value = FormatTime(aSlotStart)
                      aRept.Cells(aRowNum, 4).Value = FormatTime(aSlotEnd)
                      aRept.Cells(aRowNum, 5).Value = CStr(aRule.Duration)
                      aRept.Cells(aRowNum, 6).Value = CStr(aRule.PosID)
                      aRept.Cells(aRowNum, 7).Value = aTypeCode
                      aRept.Cells(aRowNum, 8).Value = sBookedStatus
                    End If

                  End If  'slot fits

                  aSlotStart = aSlotStart + ((aRule.Duration + aRule.Skip) / 1440)
                Loop  'slot

              End If  'CheckDayIsActive

              aDate = aDate + 1
            Loop  'aDate

          End If  'bProvGrpMatch
        End If  'bTypeMatch
      End If  'bDurationMatch
    End If  'RuleType = 1
  Next  'i

  ' --- Step 3: Save and display report ---
  aProgressBar.Position = aRuleCount
  aProgressBar.Caption  = "Saving report..."

  aRept.Save 0
  aRept.PrintIt

End Sub
