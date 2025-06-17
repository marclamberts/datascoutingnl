Sub ControleerOutlookEnVerstuurEmail()
    Dim OutlookApp As Object
    Dim OutlookNamespace As Object
    Dim Inbox As Object
    Dim Items As Object
    Dim Item As Object
    Dim Attachment As Object
    Dim Mail As Object
    Dim ws As Worksheet
    Dim wsLog As Worksheet
    Dim wsGrafiek As Worksheet
    Dim wsFouten As Worksheet
    Dim i As Long
    Dim DebiteurNummer As String
    Dim FactuurNummer As String
    Dim Referentie As String
    Dim Bestandsnaam As String
    Dim Onderwerp As String
    Dim MatchGevonden As Boolean
    Dim EmailAdres As String
    Dim TemplateTekst As String
    Dim EmailBody As String
    Dim OutlookMail As Object
    Dim VerzondenEmails As Long
    Dim EmailSubject As String
    Dim StartTijd As Single
    Dim EindTijd As Single
    Dim VerwerkingsTijd As Double
    Dim LogRij As Long
    Dim FoutRij As Long
    Dim FoundPDF As Object
    Dim TempFolderPath As String
    Dim TempFilePath As String

    VerzondenEmails = 0
    
    ' Create temporary folder if it doesn't exist
    TempFolderPath = Environ("Temp") & "\BoelsTemp\"
    If Dir(TempFolderPath, vbDirectory) = "" Then MkDir TempFolderPath

    ' Outlook openen
    On Error Resume Next
    Set OutlookApp = GetObject(, "Outlook.Application")
    If OutlookApp Is Nothing Then
        MsgBox "Outlook is niet geopend!", vbExclamation
        Exit Sub
    End If
    On Error GoTo 0

    Set OutlookNamespace = OutlookApp.GetNamespace("MAPI")
    Set Inbox = OutlookNamespace.GetDefaultFolder(6)
    Set Items = Inbox.Items

    Set ws = ThisWorkbook.Sheets("Data")
    Set wsLog = ThisWorkbook.Sheets("Log")
    Set wsGrafiek = ThisWorkbook.Sheets("Grafiek")
    Set wsFouten = ThisWorkbook.Sheets("FoutenLog")

    i = 2

    Do While ws.Cells(i, 1).Value <> ""
        If ws.Cells(i, 7).Value = "" Then
            DebiteurNummer = Trim(CStr(ws.Cells(i, 1).Value))
            FactuurNummer = Trim(CStr(ws.Cells(i, 2).Value))
            Referentie = Trim(CStr(ws.Cells(i, 3).Value))
            EmailAdres = Trim(ws.Cells(i, 9).Value)
            TemplateTekst = ws.Cells(i, 14).Value
            EmailSubject = Trim(ws.Cells(i, 15).Value)

            MatchGevonden = False
            Set FoundPDF = Nothing

            For Each Item In Items
                If Item.Class = 43 Then
                    Set Mail = Item
                    Onderwerp = LCase(Mail.Subject)

                    ' Check subject for matches
                    If InStr(1, Onderwerp, LCase(DebiteurNummer)) > 0 Or _
                       InStr(1, Onderwerp, LCase(FactuurNummer)) > 0 Or _
                       InStr(1, Onderwerp, LCase(Referentie)) > 0 Then
                        MatchGevonden = True
                        
                        ' Look for PDF attachment
                        If Mail.Attachments.Count > 0 Then
                            For Each Attachment In Mail.Attachments
                                If LCase(Right(Attachment.Filename, 4)) = ".pdf" Then
                                    Set FoundPDF = Attachment
                                    Exit For
                                End If
                            Next Attachment
                        End If
                        Exit For
                    End If

                    ' Check attachments if no subject match
                    If Mail.Attachments.Count > 0 Then
                        For Each Attachment In Mail.Attachments
                            If LCase(Right(Attachment.Filename, 4)) = ".pdf" Then
                                Bestandsnaam = LCase(Attachment.Filename)

                                If InStr(1, Bestandsnaam, LCase(DebiteurNummer)) > 0 Or _
                                   InStr(1, Bestandsnaam, LCase(FactuurNummer)) > 0 Or _
                                   InStr(1, Bestandsnaam, LCase(Referentie)) > 0 Then
                                    MatchGevonden = True
                                    Set FoundPDF = Attachment
                                    Exit For
                                End If
                            End If
                        Next Attachment
                    End If
                End If
                If MatchGevonden Then Exit For
            Next Item

            If MatchGevonden Then
                ws.Cells(i, 7).Value = "Match"
                ws.Cells(i, 7).Interior.Color = RGB(80, 200, 120)
                ws.Cells(i, 10).Value = Format(Date, "dd-mm-yyyy")

                Dim VolledigOnderwerp As String
                VolledigOnderwerp = EmailSubject & " - " & DebiteurNummer & " - " & FactuurNummer

                StartTijd = Timer

                On Error GoTo FoutAfhandeling
                Set OutlookMail = OutlookApp.CreateItem(0)

                ' Tekst verwerken: vervang enters door <br>
                EmailBody = TemplateTekst
                EmailBody = Replace(EmailBody, vbCrLf, "<br>")
                EmailBody = Replace(EmailBody, vbCr, "<br>")
                EmailBody = Replace(EmailBody, vbLf, "<br>")

                ' Save PDF attachment to temp folder if found
                If Not FoundPDF Is Nothing Then
                    TempFilePath = TempFolderPath & FoundPDF.Filename
                    FoundPDF.SaveAsFile TempFilePath
                End If

                ' E-mail versturen met HTML-handtekening en PDF attachment
                With OutlookMail
                    .To = EmailAdres
                    .Subject = VolledigOnderwerp
                    .HTMLBody = "<p>" & EmailBody & "</p>" & _
                                "<br><br><p>Met vriendelijke groet,<br>" & _
                                "<b>Special Billing</b><br>" & _
                                "Boels Verhuur B.V.<br>" & _
                                "Telefoonnummer<br>" & _
                                "E-mailadres</p>"
                    
                    ' Add PDF attachment if found
                    If Not FoundPDF Is Nothing Then
                        .Attachments.Add TempFilePath
                    End If
                    
                    .Send
                End With

                On Error GoTo 0

                ' Delete temporary PDF file
                If Dir(TempFilePath) <> "" Then Kill TempFilePath

                EindTijd = Timer
                VerwerkingsTijd = EindTijd - StartTijd

                VerzondenEmails = VerzondenEmails + 1

                LogRij = wsLog.Cells(wsLog.Rows.Count, 1).End(xlUp).Row + 1
                wsLog.Cells(LogRij, 1).Value = Now
                wsLog.Cells(LogRij, 2).Value = EmailAdres
                wsLog.Cells(LogRij, 3).Value = VolledigOnderwerp
                wsLog.Cells(LogRij, 4).Value = "Verzonden"
                wsLog.Cells(LogRij, 5).Value = Round(VerwerkingsTijd, 2)
                wsLog.Cells(LogRij, 6).Value = IIf(Not FoundPDF Is Nothing, "Met PDF", "Zonder PDF")
            Else
                ws.Cells(i, 7).Value = "Geen Match"
                ws.Cells(i, 7).Interior.Color = RGB(255, 0, 0)
                ws.Cells(i, 10).Value = Format(Date, "dd-mm-yyyy")
            End If
        End If
        i = i + 1
        GoTo VolgendeRij

FoutAfhandeling:
        FoutRij = wsFouten.Cells(wsFouten.Rows.Count, 1).End(xlUp).Row + 1
        wsFouten.Cells(FoutRij, 1).Value = Now
        wsFouten.Cells(FoutRij, 2).Value = "Fout bij e-mail aan: " & EmailAdres
        wsFouten.Cells(FoutRij, 3).Value = Err.Description
        Err.Clear
        
        ' Delete temporary PDF file if it exists
        If Dir(TempFilePath) <> "" Then Kill TempFilePath
        
        Resume Next

VolgendeRij:
    Loop

    ' Clean up - delete temp folder if empty
    On Error Resume Next
    If Dir(TempFolderPath, vbDirectory) <> "" Then
        If Dir(TempFolderPath & "*.*") = "" Then RmDir TempFolderPath
    End If
    On Error GoTo 0

    ws.Cells(1, 20).Value = "Macro afgerond: " & Now
    ws.Cells(1, 21).Value = "Verzonden e-mails: " & VerzondenEmails

    Call MaakGrafieken(wsGrafiek, wsLog)
    Call UpdateStatusOverzicht
    Call MaakUitgebreidDashboard

    MsgBox "Macro afgerond!" & vbCrLf & "Aantal verzonden e-mails: " & VerzondenEmails
End Sub

Sub MaakGrafieken(wsGrafiek As Worksheet, wsLog As Worksheet)
    Dim LastRow As Long
    Dim chtBar As ChartObject

    On Error Resume Next
    wsGrafiek.ChartObjects.Delete
    On Error GoTo 0

    LastRow = wsLog.Cells(wsLog.Rows.Count, 1).End(xlUp).Row
    If LastRow < 2 Then Exit Sub

    Set chtBar = wsGrafiek.ChartObjects.Add(Left:=10, Top:=10, Width:=600, Height:=300)
    With chtBar.Chart
        .SetSourceData Source:=wsLog.Range("A1:A" & LastRow & ",E1:E" & LastRow)
        .ChartType = xlColumnClustered

        ' Kleuren en stijlen
        With .SeriesCollection(1)
            .Format.Fill.ForeColor.RGB = RGB(0, 153, 51)  ' Groen voor bars
        End With

        .HasTitle = True
        With .ChartTitle
            .Text = "Verwerkingstijd per Datum"
            .Font.Name = "Calibri"
            .Font.Size = 16
            .Font.Bold = True
            .Font.Color = RGB(0, 102, 204)  ' Blauw
        End With

        With .Axes(xlCategory)
            .HasTitle = True
            .AxisTitle.Text = "Datum"
            .AxisTitle.Font.Name = "Calibri"
            .AxisTitle.Font.Size = 12
            .AxisTitle.Font.Bold = True
            .AxisTitle.Font.Color = RGB(0, 102, 204)
            .TickLabels.Font.Name = "Calibri"
            .TickLabels.Font.Size = 10
            .CategoryNames = wsLog.Range("A2:A" & LastRow)
        End With

        With .Axes(xlValue)
            .HasTitle = True
            .AxisTitle.Text = "Verwerkingstijd (s)"
            .AxisTitle.Font.Name = "Calibri"
            .AxisTitle.Font.Size = 12
            .AxisTitle.Font.Bold = True
            .AxisTitle.Font.Color = RGB(0, 102, 204)
            .TickLabels.Font.Name = "Calibri"
            .TickLabels.Font.Size = 10
        End With
    End With
End Sub

Sub UpdateStatusOverzicht()
    Dim wsData As Worksheet
    Dim wsLog As Worksheet
    Dim wsFouten As Worksheet
    Dim wsStatus As Worksheet
    Dim LastRowData As Long
    Dim LastRowLog As Long
    Dim LastRowFout As Long
    Dim AantalGeenMatch As Long

    On Error Resume Next
    Set wsData = ThisWorkbook.Sheets("Data")
    Set wsLog = ThisWorkbook.Sheets("Log")
    Set wsFouten = ThisWorkbook.Sheets("FoutenLog")
    Set wsStatus = ThisWorkbook.Sheets("StatusOverzicht")
    On Error GoTo 0

    If wsData Is Nothing Or wsStatus Is Nothing Then Exit Sub

    LastRowData = wsData.Cells(wsData.Rows.Count, 1).End(xlUp).Row
    LastRowLog = wsLog.Cells(wsLog.Rows.Count, 1).End(xlUp).Row
    LastRowFout = wsFouten.Cells(wsFouten.Rows.Count, 1).End(xlUp).Row

    AantalGeenMatch = WorksheetFunction.CountIf(wsData.Range("G2:G" & LastRowData), "Geen Match")

    With wsStatus
        .Cells(2, 1).Value = "Laatste Uitvoering"
        .Cells(2, 2).Value = Now

        .Cells(3, 1).Value = "Totaal verwerkte regels"
        .Cells(3, 2).Value = LastRowData - 1

        .Cells(4, 1).Value = "Aantal verzonden e-mails"
        .Cells(4, 2).Value = LastRowLog - 1

        .Cells(5, 1).Value = "Aantal 'Geen Match'"
        .Cells(5, 2).Value = AantalGeenMatch

        .Cells(6, 1).Value = "Aantal fouten"
        .Cells(6, 2).Value = LastRowFout - 1
    End With
End Sub

Sub MaakUitgebreidDashboard()
    Dim wsDash As Worksheet
    Dim wsData As Worksheet, wsLog As Worksheet, wsFouten As Worksheet
    Dim lrData As Long, lrLog As Long, lrFout As Long
    Dim totRegels As Long, totVerzonden As Long, totGeenMatch As Long, totFouten As Long
    Dim totMatch As Long, totGeenEmail As Long
    Dim UniekeEmails As Long
    Dim GemVerwerkingstijd As Double

    ' Dashboard opnieuw maken
    Application.DisplayAlerts = False
    On Error Resume Next
    Worksheets("Dashboard").Delete
    On Error GoTo 0
    Application.DisplayAlerts = True

    Set wsDash = ThisWorkbook.Sheets.Add
    wsDash.Name = "Dashboard"
    wsDash.Cells.Clear

    On Error Resume Next
    Set wsData = Sheets("Data")
    Set wsLog = Sheets("Log")
    Set wsFouten = Sheets("FoutenLog")
    On Error GoTo 0

    If wsData Is Nothing Or wsLog Is Nothing Then Exit Sub

    lrData = wsData.Cells(wsData.Rows.Count, 1).End(xlUp).Row
    lrLog = wsLog.Cells(wsLog.Rows.Count, 1).End(xlUp).Row
    lrFout = wsFouten.Cells(wsFouten.Rows.Count, 1).End(xlUp).Row

    totRegels = lrData - 1
    totVerzonden = lrLog - 1
    totGeenMatch = WorksheetFunction.CountIf(wsData.Range("G2:G" & lrData), "Geen Match")
    totMatch = WorksheetFunction.CountIf(wsData.Range("G2:G" & lrData), "Match")
    totFouten = lrFout - 1
    totGeenEmail = WorksheetFunction.CountBlank(wsData.Range("I2:I" & lrData))
    UniekeEmails = WorksheetFunction.CountIfs(wsData.Range("I2:I" & lrData), "<>""")
    If totVerzonden > 0 Then
        GemVerwerkingstijd = WorksheetFunction.Average(wsLog.Range("E2:E" & lrLog))
    Else
        GemVerwerkingstijd = 0
    End If

    With wsDash
        ' Titel
        .Range("B2:C2").Merge
        .Range("B2").Value = "Special Billing Dashboard Overzicht"
        .Range("B2").Font.Size = 20
        .Range("B2").Font.Bold = True
        .Range("B2").HorizontalAlignment = xlCenter

        ' KPI kaarten
        .Range("B4").Value = "Totaal Regels"
        .Range("C4").Value = totRegels

        .Range("B5").Value = "Verzonden E-mails"
        .Range("C5").Value = totVerzonden

        .Range("B6").Value = "Match"
        .Range("C6").Value = totMatch

        .Range("B7").Value = "Geen Match"
        .Range("C7").Value = totGeenMatch

        .Range("B8").Value = "Fouten"
        .Range("C8").Value = totFouten

        .Range("B9").Value = "Geen E-mail Adres"
        .Range("C9").Value = totGeenEmail

        .Range("B10").Value = "Unieke E-mailadressen"
        .Range("C10").Value = UniekeEmails

        .Range("B11").Value = "Gem. Verwerkingstijd (s)"
        .Range("C11").Value = Round(GemVerwerkingstijd, 2)

        ' Styling
        With .Range("B4:B11")
            .Font.Bold = True
            .Interior.Color = RGB(0, 102, 204)
            .Font.Color = vbWhite
        End With

        With .Range("C4:C11")
            .Font.Size = 12
            .Interior.Color = RGB(255, 204, 0)
        End With

        .Columns("B:C").AutoFit
    End With
End Sub
