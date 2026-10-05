// Proposed synthetic training query. Name the query SEO064_Normalized.
// Not executed in Power Query/Excel. Edit only the local training folder.
let
    InputFolder = "C:\REPLACE_WITH_TRAINING_FOLDER\",
    RawFields = {"IDRaw", "DateRaw", "ReadingRaw", "UnitRaw", "SourceResultRaw"},
    Clean = (value as nullable text) as text =>
        if value = null then "" else Text.Trim(value),
    LoadOne = (fileName as text, fieldMap as list, dateFormat as text, culture as text) as table =>
        let
            CSV = Csv.Document(
                File.Contents(InputFolder & fileName),
                [Delimiter = ",", Columns = 5, Encoding = 65001,
                 QuoteStyle = QuoteStyle.Csv, ExtraValues = ExtraValues.Error]
            ),
            Headers = Table.PromoteHeaders(CSV, [PromoteAllScalars = true]),
            ExpectedHeaders = List.Transform(fieldMap, each _{0}),
            CheckedHeaders = if List.Sort(Table.ColumnNames(Headers)) = List.Sort(ExpectedHeaders)
                then Headers else error "Unexpected training CSV headers",
            Named = Table.RenameColumns(CheckedHeaders, fieldMap, MissingField.Error),
            TextOnly = Table.TransformColumnTypes(
                Named, List.Transform(RawFields, each {_, type text}), "en-US"
            ),
            Indexed = Table.AddIndexColumn(TextOnly, "SourceRow", 1, 1, Int64.Type),
            WithFile = Table.AddColumn(Indexed, "SourceFile", each fileName, type text),
            WithFormat = Table.AddColumn(WithFile, "DateFormat", each dateFormat, type text),
            WithCulture = Table.AddColumn(WithFormat, "SourceCulture", each culture, type text)
        in
            WithCulture,
    A = LoadOne(
        "inspections_a.csv",
        {{"InspectionID", "IDRaw"}, {"InspectionDate", "DateRaw"},
         {"Reading", "ReadingRaw"}, {"Unit", "UnitRaw"}, {"Result", "SourceResultRaw"}},
        "dd/MM/yyyy", "en-GB"
    ),
    B = LoadOne(
        "inspections_b.csv",
        {{"InspectionKey", "IDRaw"}, {"DateRecorded", "DateRaw"},
         {"MeasuredValue", "ReadingRaw"}, {"LengthUnit", "UnitRaw"}, {"Outcome", "SourceResultRaw"}},
        "MM/dd/yyyy", "en-US"
    ),
    Combined = Table.Combine({A, B}),
    Parsed = Table.AddColumn(Combined, "Parsed", each
        let
            IDText = Clean([IDRaw]),
            ID = if IDText = "" then null else IDText,
            DateAttempt = try Date.FromText(
                Clean([DateRaw]), [Format = [DateFormat], Culture = [SourceCulture]]
            ),
            ParsedDate = if DateAttempt[HasError] then null else DateAttempt[Value],
            NumberAttempt = try Number.FromText(Clean([ReadingRaw]), [SourceCulture]),
            ParsedNumber = if NumberAttempt[HasError] then null else NumberAttempt[Value],
            UnitText = Text.Lower(Clean([UnitRaw])),
            ResultText = Clean([SourceResultRaw]),
            InMM = if ParsedNumber = null then null
                else if UnitText = "mm" then ParsedNumber
                else if UnitText = "cm" then ParsedNumber * 10
                else null,
            Problems = List.RemoveNulls({
                if ID = null then "missing_id" else null,
                if ParsedDate = null then "invalid_date" else null,
                if ParsedNumber = null then "invalid_reading" else null,
                if UnitText = "" then "missing_unit" else null,
                if UnitText <> "" and not List.Contains({"mm", "cm"}, UnitText)
                    then "unsupported_unit" else null,
                if ResultText = "" then "missing_source_result" else null,
                if ResultText <> "" and not List.Contains({"Pass", "Fail"}, ResultText)
                    then "unsupported_source_result" else null
            })
        in
            [InspectionID = ID, InspectionDate = ParsedDate,
             ReadingNumber = ParsedNumber, Unit = UnitText, SourceResult = ResultText,
             ReadingMM = InMM, BaseIssues = Text.Combine(Problems, ";")], type record),
    Expanded = Table.ExpandRecordColumn(Parsed, "Parsed",
        {"InspectionID", "InspectionDate", "ReadingNumber", "Unit", "SourceResult", "ReadingMM", "BaseIssues"}),
    Counts = Table.Group(
        Table.SelectRows(Expanded, each [InspectionID] <> null),
        {"InspectionID"}, {{"IDOccurrences", each Table.RowCount(_), Int64.Type}}
    ),
    Joined = Table.NestedJoin(Expanded, {"InspectionID"}, Counts,
        {"InspectionID"}, "IDCounts", JoinKind.LeftOuter),
    WithCounts = Table.ExpandTableColumn(Joined, "IDCounts", {"IDOccurrences"}),
    ZeroForMissingID = Table.ReplaceValue(WithCounts, null, 0,
        Replacer.ReplaceValue, {"IDOccurrences"}),
    WithIssues = Table.AddColumn(ZeroForMissingID, "Issues", each
        Text.Combine(List.Select(
            {[BaseIssues], if [IDOccurrences] > 1 then "duplicate_id" else ""},
            each _ <> ""), ";"), type text),
    WithState = Table.AddColumn(WithIssues, "RowState", each
        if [Issues] = "" then "ready_for_demo" else "review", type text),
    Columns = Table.SelectColumns(WithState,
        {"SourceFile", "SourceRow", "DateFormat", "SourceCulture", "IDRaw", "DateRaw",
         "ReadingRaw", "UnitRaw", "SourceResultRaw", "InspectionID", "InspectionDate",
         "ReadingNumber", "Unit", "SourceResult", "ReadingMM", "IDOccurrences", "Issues", "RowState"}),
    Typed = Table.TransformColumnTypes(Columns,
        {{"InspectionID", type text}, {"InspectionDate", type date},
         {"ReadingNumber", type number}, {"ReadingMM", type number}, {"IDOccurrences", Int64.Type}}, "en-US"),
    Sorted = Table.Sort(Typed, {{"SourceFile", Order.Ascending}, {"SourceRow", Order.Ascending}})
in
    Sorted
