from spatula import JsonPage, URL
from openstates.models import ScrapePerson
import json


class MemberList(JsonPage):
    def process_page(self):
        data = self.response.json().get("data")

        # Combine all data fields that contain a member object
        members = []
        member_fields = [
            "houseMembersNewImgUrl",
            "houseLeadersNewImgUrl",
            "senateMembersNewImgUrl",
            "senateLeadersNewImgUrl",
        ]
        for field in member_fields:
            # Ignore fields that are missing
            if data.get(field):
                members += data.get(field)

        for member in members:
            # Skip adding member if district info isn't found.
            if not member.get("District") or member.get("District") == "Not Available":
                name = member.get("FullName")
                self.logger.warning(f"{name} has no listed district, skipping.")
                continue

            p = ScrapePerson(
                name=member.get("FullName"),
                state="al",
                chamber=self.chamber,
                party=member.get("Affiliation"),
                district=member.get("District"),
                email=member.get("Email"),
                image=member.get("NewImgUrl"),
                given_name=member.get("FirstName"),
                family_name=member.get("LastName"),
            )

            p.add_source(
                self.source.url, note="graphql endpoint for member information"
            )

            # Missing data may sometimes be set to a string like "None Listed"
            capitol_address = member.get("FullAddress")
            if not capitol_address.startswith("No Address Listed"):
                p.capitol_office.address = capitol_address

            capitol_phone = member.get("Phone")
            if capitol_phone and not capitol_phone == "None Listed":
                p.capitol_office.voice = capitol_phone

            district_address = member.get("FullDistrictAddress")
            if not district_address.startswith("No District Address Listed"):
                p.district_office.address = district_address

            district_phone = member.get("DistrictPhone")
            if district_phone and not district_phone == "None Listed":
                p.district_office.voice = district_phone

            p.extras["counties"] = member.get("Counties")

            yield p


def graphql_query(data):
    return URL(
        "https://gql.api.alison.legislature.state.al.us/graphql",
        method="POST",
        headers={
            "Content-Type": "application/json",
            # Referer required or graphql will respond with http error 403
            "Referer": "https://alison.legislature.state.al.us/",
        },
        data=json.dumps(data),
    )


def get_members_source(chamber):
    chamber_type = "house" if chamber == "lower" else "senate"
    fields = "Affiliation,FullName,FirstName,LastName,NewImgUrl,District,Counties,FullAddress,Phone,Email,FullDistrictAddress,DistrictOffice,Fax,DistrictFax,DistrictPhone,DistrictEmail"
    # Need to check both Members and Leaders
    return graphql_query(
        {
            "query": "{"
            + chamber_type
            + "MembersNewImgUrl{"
            + fields
            + "} "
            + chamber_type
            + "LeadersNewImgUrl{"
            + fields
            + "}}",
            "operationName": "",
            "variables": [],
        },
    )


class RepList(MemberList):
    chamber = "lower"
    source = get_members_source(chamber="lower")


class SenList(MemberList):
    chamber = "upper"
    source = get_members_source(chamber="upper")
