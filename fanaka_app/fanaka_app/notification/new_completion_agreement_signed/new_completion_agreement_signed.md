<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #444;
            margin: 0;
            padding: 0;
            background-color: #f0f2f5;
        }
        .container {
            max-width: 650px;
            margin: 30px auto;
            background: #ffffff;
            border-radius: 4px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        .header {
            background-color: #1a1a1a;
            color: #ffffff;
            padding: 20px 30px;
            border-bottom: 4px solid #007bff;
        }
        .header h1 {
            margin: 0;
            font-size: 18px;
            font-weight: 500;
            letter-spacing: 0.5px;
        }
        .content {
            padding: 30px;
        }
        .section-header {
            margin-bottom: 15px;
            padding-bottom: 8px;
            border-bottom: 1px solid #eee;
            color: #007bff;
            font-size: 14px;
            font-weight: bold;
            text-transform: uppercase;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 25px;
        }
        th, td {
            text-align: left;
            padding: 12px 15px;
            border: 1px solid #edf2f7;
            font-size: 14px;
        }
        th {
            background-color: #f8f9fa;
            color: #666;
            width: 35%;
            font-weight: 600;
        }
        td {
            background-color: #ffffff;
            color: #1a202c;
        }
        .footer {
            background-color: #f8f9fa;
            padding: 15px 30px;
            text-align: right;
            font-size: 11px;
            color: #a0aec0;
            border-top: 1px solid #eee;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Completion Agreement: {{ doc.sale_id }}</h1>
        </div>

        <div class="content">
            <div class="section-header">Customer & Identity</div>
            <table>
                <tr>
                    <th>Customer Name</th>
                    <td>{{ doc.customer }}</td>
                </tr>
                <tr>
                    <th>ID Number</th>
                    <td>{{ doc.id_no or "N/A" }}</td>
                </tr>
                <tr>
                    <th>Phone Number</th>
                    <td>{{ doc.phone_number }}</td>
                </tr>
                <tr>
                    <th>Signed On</th>
                    <td>{{ frappe.utils.format_date(doc.signed_on) if doc.signed_on else "N/A" }}</td>
                </tr>
            </table>

            <div class="section-header">Property & Project</div>
            <table>
                <tr>
                    <th>Project Name</th>
                    <td>{{ frappe.db.get_value("Project", doc.project, "project_name") if doc.project else "N/A" }}</td>
                </tr>
                <tr>
                    <th>Plot Number</th>
                    <td>{{ frappe.db.get_value("Plot", doc.plot, "plot_no") if doc.plot else "N/A" }}</td>
                </tr>
            </table>

            <div class="section-header">Reference Links</div>
            <table>
                <tr>
                    <th>Sales Invoice</th>
                    <td>{{ doc.sales_invoice or "Not Linked" }}</td>
                </tr>
                {% if doc.amended_from %}
                <tr>
                    <th>Amended From</th>
                    <td>{{ doc.amended_from }}</td>
                </tr>
                {% endif %}
            </table>
        </div>

        <div class="footer">
            Generated via Frappe Cloud | {{ frappe.utils.now_datetime().strftime('%Y-%m-%d %H:%M') }}
        </div>
    </div>
</body>
</html>