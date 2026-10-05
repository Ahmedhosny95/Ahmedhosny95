// Proposed synthetic training query. Run after query SEO064_Normalized.
// Not executed in Power Query/Excel. ExpectedInputRows is fixed to this fixture.
let
    Source = SEO064_Normalized,
    Grouped = Table.Group(Source, {"SourceFile"}, {
        {"OutputRows", each Table.RowCount(_), Int64.Type},
        {"ReadyRows", each Table.RowCount(Table.SelectRows(_, each [RowState] = "ready_for_demo")), Int64.Type},
        {"ReviewRows", each Table.RowCount(Table.SelectRows(_, each [RowState] = "review")), Int64.Type},
        {"PassLabels", each List.Count(List.Select([SourceResult], each _ = "Pass")), Int64.Type},
        {"FailLabels", each List.Count(List.Select([SourceResult], each _ = "Fail")), Int64.Type},
        {"BlankResultLabels", each List.Count(List.Select([SourceResult], each _ = "")), Int64.Type}
    }),
    WithExpected = Table.AddColumn(Grouped, "ExpectedInputRows", each
        if List.Contains({"inspections_a.csv", "inspections_b.csv"}, [SourceFile])
        then 5 else error "Unknown fixture source", Int64.Type),
    WithBalance = Table.AddColumn(WithExpected, "RowReconciles", each
        [OutputRows] = [ExpectedInputRows] and [OutputRows] = [ReadyRows] + [ReviewRows], type logical),
    Columns = Table.SelectColumns(WithBalance,
        {"SourceFile", "ExpectedInputRows", "OutputRows", "ReadyRows", "ReviewRows",
         "PassLabels", "FailLabels", "BlankResultLabels", "RowReconciles"}),
    Sorted = Table.Sort(Columns, {{"SourceFile", Order.Ascending}})
in
    Sorted
