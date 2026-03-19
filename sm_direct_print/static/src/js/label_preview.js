/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, onMounted, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { rpc } from "@web/core/network/rpc";

/**
 * Label Preview — renders ZPL using Labelary API and shows the label image.
 */
export class LabelPreview extends Component {
    static template = "sm_direct_print.LabelPreview";
    static props = ["*"];

    setup() {
        this.action = useService("action");
        this.notification = useService("notification");
        this.state = useState({
            imageData: null,
            loading: true,
            error: null,
        });

        onMounted(() => this._loadPreview());
    }

    async _loadPreview() {
        const params = this.props.action?.params || {};
        const zpl = params.zpl || "";
        const width = params.width || 100;
        const height = params.height || 50;
        const dpi = params.dpi || "203";

        if (!zpl) {
            this.state.error = "No ZPL data to preview.";
            this.state.loading = false;
            return;
        }

        try {
            const result = await rpc("/direct_print/preview", {
                zpl, width, height, dpi,
            });

            if (result.error) {
                this.state.error = result.error;
            } else {
                this.state.imageData = `data:${result.content_type};base64,${result.image}`;
            }
        } catch (e) {
            this.state.error = `Preview failed: ${e}`;
        }
        this.state.loading = false;
    }

    goBack() {
        this.action.restore();
    }
}

registry.category("actions").add("sm_direct_print.label_preview", LabelPreview);
