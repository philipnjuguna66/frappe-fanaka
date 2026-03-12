frappe.listview_settings['Requisitions'] = {

    onload(listview) {

        const statuses = ["pending","approved","rejected","paid","submitted"];

        setTimeout(() => {

            let container = listview.page.wrapper.find('.custom-status-buttons');

            if (container.length) return;

            container = $(`<div class="custom-status-buttons" style="margin-bottom:10px;"></div>`);
            listview.page.wrapper.find('.layout-main-section').prepend(container);

            // ALL BUTTON
            let all_btn = $(`<button class="btn btn-sm btn-default">All</button>`);

            all_btn.click(() => {
                listview.filter_area.clear();
                listview.refresh();
            });

            container.append(all_btn);

            statuses.forEach(status => {

                let label = status.charAt(0).toUpperCase() + status.slice(1);

                let btn = $(`<button class="btn btn-sm btn-default" style="margin-left:5px;">${label.toUpperCase()}</button>`);

                btn.click(() => {

                    listview.filter_area.remove("status");

                    listview.filter_area.add(
                        "Requisitions",
                        "status",
                        "=",
                        status
                    );

                    listview.refresh();
                });

                container.append(btn);
            });

        }, 300);
    }
};