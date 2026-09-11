## PART 0 - REQUIREMENTS
#### WHAT I WILL BE BUILDING
My understanding is that, we need a proper **member-callout** system for local leadership to send important callouts to the right members and easily see who has received, read, and acknowledged them. Each local’s information will remain private, and the system will make sure members don’t receive the same callout twice. I’ll also include AI assistance to help leaders turn messy or ambiguous announcements into a clear message before they approve and send it.


#### ASSUMPTIONS
Following are some major assumptions that i would consider when designing this system:
- This system mainly incorporates 2 roles i.e: Leadership and Members. And data accessibility authority is imposed as per the role.
- Members and Leaders can only view information relevant to their own local.
- Only Active members of the selected local receives their respective call out.
- Members should not receive same callout notification twice.
- The leader needs to know how many members have responded to the callout, rather than having a full attendance tracking system.
- Members must receive the callout notification in advance of the scheduled meeting time ( given that their mobile is connected ).
- AI generated content will process further only upon leader's approval.

#### POINT OF CONCERN

Some of the major areas of concern that i noticed:
-  Members must only access data from their own local.
- Suspended and retired members must lose access of their local immediately.

#### QUESTIONS TO BE ASKED FROM DENISE

- Should callouts target all active members of a local, or should leadership be able to target specific classifications, locations and shifts?

(Assumption: All active members of that specific local by default)
- What information may members see about one another?

(Assumption: Members can view only the email addresses of members within their own local. )
- What does “Sent” mean? queued for delivery, delivered to the member, or read by the member?

(Assumption: “Sent” means the announcement has been accepted and queued for background delivery to the selected recipients; it does not mean it was delivered, opened or acknowledged.)
