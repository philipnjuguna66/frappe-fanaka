// Copyright (c) 2026, Fanaka Real Estate Ltd. and contributors
/* eslint-disable */

frappe.query_reports["P9 Form"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
		},
		{
			fieldname: "employee",
			label: __("Employee"),
			fieldtype: "Link",
			options: "Employee",
			reqd: 1,
			get_query: function () {
				const company = frappe.query_report.get_filter_value("company");
				return company ? { filters: { company: company } } : {};
			},
		},
		{
			fieldname: "year",
			label: __("Year"),
			fieldtype: "Select",
			reqd: 1,
			options: p9_year_options(),
			default: String(new Date().getFullYear()),
		},
	],

	formatter: function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (data && data.is_total) {
			value = `<b>${value}</b>`;
		}
		return value;
	},

	onload: function (report) {
		report.page.add_inner_button(__("🖨 Print KRA P9 Card"), function () {
			const employee = frappe.query_report.get_filter_value("employee");
			const year = frappe.query_report.get_filter_value("year");
			const company = frappe.query_report.get_filter_value("company");
			if (!employee || !year) {
				frappe.msgprint(__("Select Employee and Year first."));
				return;
			}
			frappe.call({
				method: "fanaka_app.api.p9.get_p9_data",
				args: { employee, year, company },
				freeze: true,
				callback: function (r) {
					if (r.message) p9_open_print_card(r.message);
				},
			});
		});
	},
};

function p9_year_options() {
	const now = new Date().getFullYear();
	const years = [];
	for (let y = now; y >= now - 10; y--) years.push(String(y));
	return years.join("\n");
}

function p9_fmt(n) {
	return (flt(n) || 0).toLocaleString("en-KE", {
		minimumFractionDigits: 2,
		maximumFractionDigits: 2,
	});
}

function p9_open_print_card(d) {
	const rows = d.months
		.map(
			(m) => `
		<tr>
			<td class="l">${m.month}</td>
			<td>${p9_fmt(m.basic)}</td>
			<td>${p9_fmt(m.benefits)}</td>
			<td>${p9_fmt(m.gross)}</td>
			<td>${p9_fmt(m.nssf)}</td>
			<td>${p9_fmt(m.nhif)}</td>
			<td>${p9_fmt(m.shif)}</td>
			<td>${p9_fmt(m.ahl)}</td>
			<td>${p9_fmt(m.taxable)}</td>
			<td>${p9_fmt(m.personal_relief)}</td>
			<td>${p9_fmt(m.insurance_relief)}</td>
			<td>${p9_fmt(m.paye)}</td>
			<td>${p9_fmt(m.net_pay)}</td>
		</tr>`
		)
		.join("");

	const t = d.totals;
	const total_row = `
		<tr class="totals">
			<td class="l">Totals</td>
			<td>${p9_fmt(t.basic)}</td>
			<td>${p9_fmt(t.benefits)}</td>
			<td>${p9_fmt(t.gross)}</td>
			<td>${p9_fmt(t.nssf)}</td>
			<td>${p9_fmt(t.nhif)}</td>
			<td>${p9_fmt(t.shif)}</td>
			<td>${p9_fmt(t.ahl)}</td>
			<td>${p9_fmt(t.taxable)}</td>
			<td>${p9_fmt(t.personal_relief)}</td>
			<td>${p9_fmt(t.insurance_relief)}</td>
			<td>${p9_fmt(t.paye)}</td>
			<td>${p9_fmt(t.net_pay)}</td>
		</tr>`;

	const html = `<!doctype html>
<html><head><meta charset="utf-8"><title>P9 Form - ${frappe.utils.escape_html(d.employee.name)} (${d.year})</title>
<style>
	* { box-sizing: border-box; }
	body { font-family: "Helvetica Neue", Arial, sans-serif; color: #1f272e; margin: 24px; font-size: 12px; }
	.head { display:flex; justify-content:space-between; align-items:flex-start; border-bottom:2px solid #2b3744; padding-bottom:8px; }
	.head h1 { font-size:22px; margin:0; letter-spacing:.5px; }
	.head .yr { font-size:12px; color:#555; margin-top:4px; }
	.head .kra { text-align:right; font-weight:700; font-size:13px; line-height:1.5; }
	h3 { font-size:13px; margin:18px 0 6px; color:#2b3744; }
	.grid { display:grid; grid-template-columns:1fr 1fr; gap:10px 20px; }
	.grid3 { grid-template-columns:1fr 1fr 1fr; }
	.fld label { display:block; font-size:10px; color:#777; margin-bottom:2px; }
	.fld .box { border:1px solid #cfd6dd; border-radius:4px; padding:7px 9px; min-height:30px; }
	table { width:100%; border-collapse:collapse; margin-top:6px; }
	th, td { border:1px solid #cfd6dd; padding:5px 6px; text-align:right; font-size:10.5px; }
	th { background:#f4f6f8; font-weight:700; }
	td.l, th.l { text-align:left; }
	thead .grp th { background:#eef1f4; }
	tr.totals td { font-weight:700; background:#f4f6f8; }
	.sign { display:flex; justify-content:space-between; margin-top:40px; }
	.sign .col { width:45%; text-align:center; }
	.sign .line { border-top:1px dotted #888; padding-top:6px; font-size:11px; }
	.note { margin-top:24px; font-size:9.5px; color:#888; }
	@media print { body { margin:0; padding:14px; } .noprint { display:none; } @page { size:A4 landscape; margin:10mm; } }
	.bar { margin-bottom:14px; }
	.bar button { padding:8px 16px; font-size:13px; cursor:pointer; border:1px solid #2b3744; background:#2b3744; color:#fff; border-radius:4px; }
</style></head>
<body>
	<div class="bar noprint"><button onclick="window.print()">Print / Save as PDF</button></div>

	<div class="head">
		<div>
			<h1>TAX DEDUCTION CARD</h1>
			<div class="yr">YEAR: ${d.year}</div>
		</div>
		<div class="kra">KENYA REVENUE AUTHORITY<br>DOMESTIC TAXES DEPARTMENT</div>
	</div>

	<h3>A. Employer Details</h3>
	<div class="grid">
		<div class="fld"><label>Employer's Name</label><div class="box">${frappe.utils.escape_html(d.employer.name || "")}</div></div>
		<div class="fld"><label>Employer's PIN</label><div class="box">${frappe.utils.escape_html(d.employer.pin || "")}</div></div>
	</div>

	<h3>B. Employee Details</h3>
	<div class="grid grid3">
		<div class="fld"><label>Employee's Name</label><div class="box">${frappe.utils.escape_html(d.employee.name || "")}</div></div>
		<div class="fld"><label>Employee's PIN</label><div class="box">${frappe.utils.escape_html(d.employee.pin || "")}</div></div>
		<div class="fld"><label>Employee's Employment No.</label><div class="box">${frappe.utils.escape_html(d.employee.id || "")}</div></div>
	</div>

	<h3>C. Monthly Income and Deductions</h3>
	<table>
		<thead>
			<tr class="grp">
				<th class="l" rowspan="2">Month</th>
				<th colspan="3">Gross Pay (Kshs.)</th>
				<th colspan="4">Allowable Deductions (Kshs.)</th>
				<th rowspan="2">Taxable Income</th>
				<th colspan="2">Reliefs (Kshs.)</th>
				<th rowspan="2">Net Payee (PAYE)</th>
				<th rowspan="2">Net Pay</th>
			</tr>
			<tr>
				<th>Basic Salary</th><th>Benefits</th><th>Total Gross</th>
				<th>NSSF</th><th>NHIF</th><th>SHIF</th><th>AHL</th>
				<th>Personal Relief</th><th>Insurance Relief</th>
			</tr>
		</thead>
		<tbody>
			${rows}
			${total_row}
		</tbody>
	</table>

	<div class="sign">
		<div class="col"><div class="line">Employer's Signature &amp; Stamp &nbsp;&nbsp; Date: __ __ / __ __ / 20 __ __</div></div>
		<div class="col"><div class="line">Employee's Signature &nbsp;&nbsp; Date: __ __ / __ __ / 20 __ __</div></div>
	</div>

	<div class="note">Generated from Salary Slips. For official tax matters refer to the KRA iTax portal.</div>
</body></html>`;

	const w = window.open("", "_blank");
	w.document.write(html);
	w.document.close();
}
