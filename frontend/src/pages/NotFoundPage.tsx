import { ArrowLeft } from "lucide-react";
import { NavLink, useLocation } from "react-router-dom";

import { PageHeader } from "../components/ui/PageHeader";

export function NotFoundPage() {
  const location = useLocation();

  return (
    <div className="space-y-6">
      <PageHeader
        title="Page not found"
        description="The requested workspace view does not exist. Return to the overview to continue the analysis."
        actions={
          <NavLink
            to={{ pathname: "/overview", search: location.search }}
            className="btn btn-primary"
          >
            <ArrowLeft className="h-4 w-4" aria-hidden="true" />
            Back to overview
          </NavLink>
        }
      />
      <div className="panel panel-pad">
        <p className="text-sm text-muted">
          Available views are Overview, Forecast Explorer, Accuracy Analysis and Methodology.
        </p>
      </div>
    </div>
  );
}
