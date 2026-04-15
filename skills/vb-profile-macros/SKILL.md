' Populate server-side provider filter from the resolved IDs:
' aProvCode  = Provider.Code string (the dictionary KEY   — alphanumeric, e.g. "SMITH")
' aProviderCodeDict(aProvCode) = Provider.ID integer (the dictionary VALUE — e.g. 1042)
If aProviderCodeDict.Count > 0 Then
  Dim aProvCode
  For Each aProvCode In aProviderCodeDict.Keys
    aFilter.Providers.Add aProviderCodeDict(aProvCode)   ' pass the integer ID value, not the code key
  Next  'aProvCode
End If
