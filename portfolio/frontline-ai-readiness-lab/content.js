/* Frontline AI Readiness Lab: learning content and synthetic data.
   Everything here is fictional. Northfield Card Services, Relay Assist,
   the people, the knowledge articles and every metric are invented for this work sample. */
(function () {
  "use strict";

  var competencies = [
    { id: "prompt", short: "Brief", name: "Brief the AI clearly", desc: "Give context, task, limits and format so the first draft is usable." },
    { id: "verify", short: "Verify", name: "Verify before you send", desc: "Check every AI draft against the account and the knowledge article." },
    { id: "protect", short: "Protect", name: "Protect customer data", desc: "Approved tools only, and only the details the task needs." },
    { id: "judge", short: "Judge", name: "Own the judgment call", desc: "Spot the contacts that need a human decision or an escalation." },
    { id: "improve", short: "Improve", name: "Coach and close the loop", desc: "Report what the tool gets wrong, share what works, coach others through the change." }
  ];

  var roles = [
    { id: "agent", name: "Contact center agent", desc: "You handle live chats and calls from cardholders." },
    { id: "backoffice", name: "Back-office specialist", desc: "You work disputes and written cases from a queue." },
    { id: "leader", name: "Team leader", desc: "You coach a team of agents through the rollout." }
  ];

  var experience = [
    { id: "new", name: "New to it", desc: "I have barely used generative AI." },
    { id: "some", name: "Occasional user", desc: "I use it now and then." },
    { id: "daily", name: "Daily user", desc: "It is part of how I work." }
  ];

  /* Extra priority by role when the path is built. */
  var roleWeights = {
    agent: { verify: 0.15, judge: 0.1 },
    backoffice: { verify: 0.15, protect: 0.15 },
    leader: { improve: 0.3, judge: 0.1 }
  };

  /* ---------- Diagnostic: one scenario per competency ---------- */
  var diagnostic = [
    {
      id: "d-prompt", comp: "prompt",
      stem: {
        base: "You want Relay Assist to draft a reply about a late fee. Which request gives you the most usable first draft?",
        leader: "An agent asks how to get better drafts from Relay Assist on late-fee contacts. Which request would you show them as the model?"
      },
      options: [
        { t: "“Write a reply about a late fee.”", s: 0 },
        { t: "“Customer disputes a $39 late fee. Payment posted 2 days after the due date, account in good standing, no waiver in 12 months. Draft a short, warm chat reply applying the courtesy waiver. Stay within KA-4417.”", s: 1 },
        { t: "“Draft a warm reply about a late-fee waiver, under 80 words.”", s: 0.5 },
        { t: "“Be very apologetic and give the customer whatever keeps them happy.”", s: 0 }
      ]
    },
    {
      id: "d-verify", comp: "verify",
      stem: {
        base: "Relay Assist drafts: “Your payment was received on time, so I have removed the fee.” The account screen shows the payment posted two days after the due date. What do you do?",
        leader: "On a QA review you find this draft was sent as written: “Your payment was received on time, so I have removed the fee.” The account shows the payment posted two days late. What should the agent have done?"
      },
      options: [
        { t: "Send it. The assistant can see the account data.", s: 0 },
        { t: "Regenerate the draft until it reads correctly, then send.", s: 0.5 },
        { t: "Correct the draft to match the account and the knowledge article, then send.", s: 1 },
        { t: "Send it and add “please check your statement to confirm.”", s: 0 }
      ]
    },
    {
      id: "d-protect", comp: "protect",
      stem: {
        base: "A customer types their full card number and security code into the chat. You are about to ask Relay Assist to summarize the conversation. What is the right move?",
        backoffice: "A customer letter in your queue includes their full card number and security code. You are about to ask Relay Assist to summarize the case. What is the right move?",
        leader: "An agent asks you: “The customer typed their full card number and security code into chat. Can I paste the conversation into Relay Assist for a summary?” What do you tell them?"
      },
      options: [
        { t: "Paste all of it. Relay Assist is an approved tool.", s: 0 },
        { t: "Paste it, then delete the conversation afterwards.", s: 0 },
        { t: "Leave the card number and security code out of the prompt, tell the customer not to share them, and follow the redaction step.", s: 1 },
        { t: "Leave the card details out of the prompt and carry on.", s: 0.5 }
      ]
    },
    {
      id: "d-judge", comp: "judge",
      stem: {
        base: "A customer says they lost their job and cannot keep up with payments. Relay Assist suggests: “Offer the standard late-fee waiver and close the contact.” What do you do?",
        leader: "An agent tells you a customer mentioned losing their job. Relay Assist suggested: “Offer the standard late-fee waiver and close the contact.” What do you coach?"
      },
      options: [
        { t: "Follow the suggestion. It is drawn from thousands of similar contacts.", s: 0 },
        { t: "Apply the waiver and leave a note so the next agent can pick up the hardship question.", s: 0.5 },
        { t: "Ask Relay Assist whether this counts as hardship and do what it says.", s: 0 },
        { t: "Treat it as a hardship signal, follow the hardship procedure, and treat the AI suggestion as incomplete.", s: 1 }
      ]
    },
    {
      id: "d-improve", comp: "improve",
      stem: {
        base: "You notice Relay Assist keeps quoting an out-of-date fee amount. What is the most useful thing to do?",
        leader: "Four weeks into the rollout, half your team rarely opens Relay Assist. What do you do first?"
      },
      options: {
        base: [
          { t: "Correct it each time and move on.", s: 0.5 },
          { t: "Flag the draft with the reason, and raise the pattern with your team leader.", s: 1 },
          { t: "Stop using the tool for fee questions.", s: 0 },
          { t: "Assume someone has already reported it.", s: 0 }
        ],
        leader: [
          { t: "Set a daily usage target and report against it.", s: 0 },
          { t: "Sit with two or three agents during live work to see what gets in the way, then coach on what you find.", s: 1 },
          { t: "Send the launch training link again.", s: 0 },
          { t: "Ask your strongest user to share tips at the next huddle.", s: 0.5 }
        ]
      }
    }
  ];

  /* ---------- Lessons: one per competency, role-adapted ---------- */
  var lessons = {
    prompt: {
      title: "Brief the AI like a new teammate",
      hook: {
        agent: "You have a customer waiting and twenty seconds to get a usable draft. A vague request gets you a vague reply that you will rewrite anyway.",
        backoffice: "You have forty cases in the queue. Every rewrite of a weak AI draft costs the minutes the tool was meant to save.",
        leader: "When an agent says the AI drafts are useless, look first at what they asked for."
      },
      modelName: "Context · Task · Limits · Format",
      model: {
        base: [
          ["Context", "The two or three case facts that change the answer."],
          ["Task", "What you want produced."],
          ["Limits", "What it must not say or promise. Name the knowledge article."],
          ["Format", "Length, tone and channel."]
        ]
      },
      example: {
        label: "Same contact, two requests",
        before: "Write a reply about a late fee.",
        after: "Customer disputes a $39 late fee. Payment posted 2 days after the due date. Account in good standing, no waiver in the last 12 months. Draft a chat reply applying the courtesy waiver. Stay within KA-4417 and make no promises about future fees. Under 90 words, warm, plain language.",
        note: "No name and no card number. The assistant does not need them for this job."
      },
      check: {
        stem: "Which part is missing from this request? “Customer's dispute was declined because the merchant showed proof of delivery. Write a reply. Keep it under 100 words and friendly.”",
        options: [
          { t: "Context", ok: false, fb: "The case facts are there: a declined dispute and the reason." },
          { t: "Task", ok: false, fb: "“Write a reply” is the task." },
          { t: "Limits", ok: true, fb: "Nothing tells the assistant what it cannot offer, such as a goodwill credit or a second review. That gap is where over-promising comes from." },
          { t: "Format", ok: false, fb: "Length and tone are both given." }
        ]
      },
      stretch: {
        stem: "A teammate's request has all four parts, but the drafts still come back generic. What is the most likely fix?",
        options: [
          { t: "Add “be more specific” to the request.", ok: false, fb: "The assistant cannot be specific about facts it was never given." },
          { t: "Paste in the customer's full account history.", ok: false, fb: "More data is not better context, and it is more exposure." },
          { t: "Give the two or three facts that change the answer, and name the knowledge article.", ok: true, fb: "Context means the facts that matter for this case. That is what turns a template into a reply." },
          { t: "Regenerate until one version fits.", ok: false, fb: "Each version guesses from the same thin brief." }
        ]
      },
      explain: {
        ask: "In a sentence or two: why does telling the assistant its limits matter as much as telling it the task?",
        ideas: [
          { label: "ties limits to policy or the knowledge article", re: "polic|knowledge article|article|rule|allowed|guideline|ka-" },
          { label: "names the risk of over-promising", re: "promis|commit|offer|guarantee|make up|invent|fill" },
          { label: "connects it to the customer or to rework", re: "customer|trust|complain|rework|rewrite|fix|correct|deliver" }
        ],
        model: "Without limits the assistant fills gaps with whatever sounds helpful, including promises policy does not allow. Stating the limits keeps the draft inside what we can deliver."
      },
      tutor: [
        { q: "Why not regenerate until the draft is good?", a: "Regenerating changes the wording, not the information the assistant has. If the request is missing the facts or the limits, every version guesses. Fix the brief once and the first draft is usually close.", ask: "What is one fact from your last contact that would have changed the draft?" },
        { q: "How long should a request be?", a: "Long enough to carry the four parts, short enough to type during a contact. Two to four lines is typical. If you are writing a paragraph, you are probably pasting in more than the assistant needs.", ask: "Which of the four parts do you tend to leave out?" },
        { q: "Should I include the customer's name?", a: "Not unless the task needs it. A reply drafted for “the customer” works as well, and you add the name yourself. Minimum necessary applies to prompts as much as to case notes.", ask: "What else do you paste out of habit that the assistant does not need?" }
      ]
    },

    verify: {
      title: "Verify before you send",
      hook: {
        agent: "Relay Assist writes fluent, confident sentences. Fluent is not the same as correct, and the customer cannot tell the difference. You can.",
        backoffice: "A written response is a record. If an AI draft misstates a date or an amount, that error sits in the case file under your name.",
        leader: "The most common QA failure in an AI rollout is a correct-sounding draft sent unchecked. Your agents need a check they can run in ten seconds."
      },
      modelName: "The ten-second check: Numbers · Promises · Fit",
      model: {
        base: [
          ["Numbers", "Every amount and date matches the account screen."],
          ["Promises", "Everything offered is in the knowledge article."],
          ["Fit", "It answers what this customer asked."],
          ["Then", "Fix it, or do not send it."]
        ]
      },
      example: {
        label: "One draft, checked",
        before: "Your payment arrived on time, so I have removed the fee and this month's interest.",
        after: "Numbers: wrong. The payment posted two days late. Promises: wrong. The waiver covers the fee, not interest. Fit: fine. Two fixes before this goes anywhere.",
        note: "The draft read well. Both errors were in the details a customer would act on."
      },
      check: {
        stem: "The draft says: “Your replacement card will arrive in 3 to 5 business days.” The knowledge article says 5 to 7. The customer travels on day 6. What do you do?",
        options: [
          { t: "Send it as written.", ok: false, fb: "The customer plans a trip around a date the article does not support." },
          { t: "Change it to 5 to 7 days and mention the expedited option the article lists.", ok: true, fb: "Numbers corrected against the source, and the reply now fits what this customer needs." },
          { t: "Delete the timeframe so you cannot be wrong.", ok: false, fb: "Removing the detail removes the answer the customer needs for their trip." },
          { t: "Ask the assistant if it is sure.", ok: false, fb: "It will usually say yes. The article is the source, not the assistant." }
        ]
      },
      stretch: {
        stem: "Which draft is the riskiest to send unchecked?",
        options: [
          { t: "A greeting and an apology.", ok: false, fb: "Low risk. Nothing here can be factually wrong about the account." },
          { t: "A summary of what the customer said.", ok: false, fb: "Worth a glance, but the customer is not acting on it." },
          { t: "A reply with a fee amount, a date and what happens next.", ok: true, fb: "Every number and every promise is a place a confident error can hide." },
          { t: "A closing line.", ok: false, fb: "Low risk." }
        ]
      },
      explain: {
        ask: "Explain to a new teammate why an AI draft that sounds right still needs checking.",
        ideas: [
          { label: "separates sounding right from being right", re: "sound|fluent|confiden|convinc|plausib|look|seem|read" },
          { label: "names the source to check against", re: "account|knowledge article|article|source|polic|record|system|screen" },
          { label: "names the consequence or who is accountable", re: "customer|wrong|error|mistake|accountab|responsib|complain|harm|my name" }
        ],
        model: "The assistant produces likely-sounding text. It does not know this customer's account. Numbers and promises have to match the account and the knowledge article, and the person who sends the reply is accountable for it."
      },
      tutor: [
        { q: "Why does it get things wrong if it has the articles?", a: "It predicts likely wording from patterns. Even with the right article available it can blend details, use an older version, or fill a gap with something plausible. So the check is against the source, never against how sure the draft sounds.", ask: "On a fee reply, which would you check first: the amount, the date, or the promise?" },
        { q: "Does checking cancel out the time saved?", a: "A targeted check takes about ten seconds: numbers, promises, fit. Rewriting from scratch takes minutes, and a wrong answer costs a repeat contact or a complaint. The check is what makes the saved time safe to keep.", ask: "Where in your day would ten seconds per contact be hardest to find?" },
        { q: "What if I am not sure the draft is wrong?", a: "Then the article decides. If the article does not cover it, that is a question for your team leader, and worth flagging so the article gets updated.", ask: "When did you last find an article that did not cover a real case?" }
      ]
    },

    protect: {
      title: "Protect customer data",
      hook: {
        agent: "Customers overshare, especially when they are upset. What they type into chat does not have to end up in your prompt.",
        backoffice: "Case files hold everything: statements, IDs, letters. The assistant needs a fraction of it to help you.",
        leader: "Under time pressure your team will copy what you do, not what the policy slide said."
      },
      modelName: "Minimum necessary",
      model: {
        base: [
          ["Approved tools only", "Customer information never goes into a personal or public AI app."],
          ["Leave out", "Full card numbers, security codes, ID numbers, passwords. Never in a prompt."],
          ["Describe, do not paste", "Give the facts of the case in your own words, not the raw record."],
          ["Report early", "If data goes somewhere it should not, report it straight away."]
        ]
      },
      example: {
        label: "Pasting the record versus describing the case",
        before: "[Full chat transcript pasted, including card number and date of birth]",
        after: "Customer disputes a duplicate $64.10 charge from a grocery merchant on the 12th. One charge is pending, one has posted. Summarize the case in three lines for the dispute form.",
        note: "Everything the assistant needs. Nothing that identifies the customer."
      },
      check: {
        stem: "You want help summarizing a long dispute letter that includes the customer's card number and date of birth. What goes into the approved assistant?",
        options: [
          { t: "The whole letter. It is an approved tool.", ok: false, fb: "Approved covers the tool for a purpose. The summary does not need a card number or a date of birth." },
          { t: "The letter with the card number and date of birth removed or masked.", ok: true, fb: "The assistant gets what the task needs and nothing else." },
          { t: "Nothing. AI cannot be used on disputes.", ok: false, fb: "It can. The skill is choosing what it needs." },
          { t: "A photo of the letter.", ok: false, fb: "A photo carries every sensitive detail with it." }
        ]
      },
      stretch: {
        stem: "A teammate says: “Relay Assist is approved, so anything in the case can go in.” What is the best correction?",
        options: [
          { t: "Approved means approved for the task, with the least data the task needs.", ok: true, fb: "Approval sets where you can work. Minimum necessary sets what you bring." },
          { t: "That is right.", ok: false, fb: "Every extra copy of an identifier is one more place it can surface." },
          { t: "Approved tools are still risky, so avoid them.", ok: false, fb: "Avoidance loses the benefit and usually pushes people toward unapproved tools." },
          { t: "Only team leaders may paste case data.", ok: false, fb: "The rule is about the data, not the job title." }
        ]
      },
      explain: {
        ask: "In your own words: what does “minimum necessary” mean when you write a prompt?",
        ideas: [
          { label: "limits the prompt to what the task needs", re: "only|just|minimum|least|need|necessar|nothing (else|more)|no more" },
          { label: "names identifiers to leave out", re: "card|security code|cvv|ssn|sensitive|personal|identif|date of birth|dob|id number|password" },
          { label: "says how: approved tool, describe, mask or remove", re: "approved|describe|own words|mask|redact|leave out|remove|strip|without" }
        ],
        model: "Give the assistant only the facts the task needs, described in your own words, and leave out identifiers such as card numbers and security codes, even in an approved tool."
      },
      tutor: [
        { q: "If the tool is approved, why does it matter what I paste?", a: "Approval covers the tool for a purpose. Every extra copy of a card number or an ID is one more place it can be logged or resurface in a summary. The assistant does not need it to draft a fee reply, so the safest copy is the one that is never made.", ask: "What is one detail you paste out of habit that the assistant does not need?" },
        { q: "What counts as sensitive?", a: "Full card numbers, security codes, government ID numbers, passwords and one-time codes, full dates of birth, and health or hardship details beyond what the task needs. When unsure, describe the situation in place of pasting the record.", ask: "Which of those shows up most often in your contacts?" },
        { q: "What if I already pasted something I should not have?", a: "Report it straight away through the incident process and tell your team leader. Early reports are routine and fixable. The ones that cause harm are the ones nobody mentioned.", ask: "Do you know where the incident form lives? Finding it now saves time later." }
      ]
    },

    judge: {
      title: "Own the judgment call",
      hook: {
        agent: "Relay Assist will suggest a next step on every contact. It has never been accountable for one.",
        backoffice: "The assistant sees a case type. You see the person in the file and the detail that does not fit the pattern.",
        leader: "Agents who over-trust the tool stop noticing exceptions. Agents who under-trust it never use it. Your job is the ground in between."
      },
      modelName: "Three triggers that make it your call",
      model: {
        base: [
          ["Conflict", "The AI output disagrees with the policy or the account. Policy wins. Flag the mismatch."],
          ["Vulnerability", "Job loss, illness, bereavement, distress. Follow the hardship procedure."],
          ["Out of pattern", "Complaints, legal or regulator language, anything the article does not cover. Escalate."],
          ["Always", "AI drafts. You decide."]
        ]
      },
      example: {
        label: "A suggestion that misses the point",
        before: "Customer: “My husband passed away last month and I do not know what is on this account.” Assistant suggests: “Send balance summary.”",
        after: "Trigger: vulnerability. This is a bereavement contact. Follow the bereavement procedure and slow down. A balance summary answers a question the customer did not ask.",
        note: "The suggestion matched the words. It missed the situation."
      },
      check: {
        stem: "Relay Assist's suggestion and the knowledge article disagree about whether a fee can be waived. Which do you follow?",
        options: [
          { t: "The assistant. It learns from more recent contacts.", ok: false, fb: "Recent patterns are not policy. The article is the authority." },
          { t: "The knowledge article, and flag the mismatch.", ok: true, fb: "Policy wins, and the flag is how the tool gets corrected for everyone else." },
          { t: "Whichever is better for the customer.", ok: false, fb: "Well meant, but two customers with the same case then get different answers." },
          { t: "Neither. Transfer the contact.", ok: false, fb: "The article answers this one. A transfer adds wait time without adding judgment." }
        ]
      },
      stretch: {
        stem: "Which contact most needs your judgment over the AI's suggestion?",
        options: [
          { t: "A balance inquiry.", ok: false, fb: "Routine. The pattern fits." },
          { t: "An address change.", ok: false, fb: "Routine, with a verification step the article covers." },
          { t: "A customer who mentions a regulator and says they were treated unfairly.", ok: true, fb: "Regulator and fairness language is out of pattern. It needs a person and the complaints procedure." },
          { t: "A payment date question.", ok: false, fb: "Routine. Check the date against the account." }
        ]
      },
      explain: {
        ask: "Explain why the final decision on a contact stays with a person, even when the assistant is usually right.",
        ideas: [
          { label: "names accountability", re: "accountab|responsib|own|answer for|my name" },
          { label: "names what the assistant misses", re: "exception|vulnerab|hardship|context|does not fit|doesn't fit|unusual|judg|situation|pattern|human|person" },
          { label: "points to policy or escalation", re: "polic|escalat|procedure|complain|article|rule" }
        ],
        model: "The assistant matches patterns. It is not accountable, and it misses exceptions such as hardship or a complaint. A person owns the outcome, applies policy to the case in front of them, and escalates when it does not fit."
      },
      tutor: [
        { q: "Is the AI not usually right?", a: "Often, on routine contacts. The cost sits in the exceptions: a hardship signal handled as a fee question, a complaint closed as resolved. Those are rare, high impact, and exactly what pattern matching misses.", ask: "Which of the three triggers would be easiest to miss on a busy day?" },
        { q: "Will I be marked down for overriding the AI?", a: "Following written policy over an AI suggestion is always the right call, and flagging the mismatch helps fix the tool. The risk runs the other way: sending something wrong because the assistant suggested it.", ask: "Have you seen a suggestion that conflicted with an article? What did you do?" },
        { q: "When do I escalate instead of deciding?", a: "When the article does not cover the situation, when an exception needs approval, or when the customer uses complaint, legal or regulator language. Escalating with a clear summary is good judgment.", ask: "What would you put in a two-line escalation summary?" }
      ]
    },

    improve: {
      title: "Coach and close the loop",
      hook: {
        agent: "You will spot the tool's mistakes before anyone else does. What you do next decides whether the next agent hits the same one.",
        backoffice: "You will spot the tool's mistakes before anyone else does. What you do next decides whether the next specialist hits the same one.",
        leader: "Adoption does not come from the launch email. It comes from the conversations you have in week three, when the novelty has worn off."
      },
      modelName: { base: "Flag · Share · Ask", leader: "The coaching loop: Observe · Ask · Agree · Follow up" },
      model: {
        base: [
          ["Flag", "Use the feedback control and say why the draft was wrong."],
          ["Share", "Bring one thing that worked to the team huddle."],
          ["Ask", "Tell your leader what gets in the way. That is data, not complaining."],
          ["Why", "Your flag becomes a test case for the next release."]
        ],
        leader: [
          ["Observe", "Watch real work. The dashboard shows what, not why."],
          ["Ask", "Before telling: “Walk me through how you decided the draft was ready.”"],
          ["Agree", "One specific habit, not five."],
          ["Follow up", "Within a week, on real contacts."]
        ]
      },
      example: {
        base: {
          label: "Feedback that gets acted on",
          before: "Thumbs down.",
          after: "Thumbs down, with: “Draft quoted a $35 late fee. The fee has been $39 since January. See KA-4417.”",
          note: "The second one can be triaged in a minute. The first one waits."
        },
        leader: {
          label: "Coaching that changes a habit",
          before: "“You need to use the tool more.”",
          after: "“On your next five fee contacts, try the four-part request. We will look at two of them together on Thursday.”",
          note: "Specific, small, and it has a follow-up date."
        }
      },
      check: {
        base: {
          stem: "Which feedback will get a wrong draft fixed?",
          options: [
            { t: "A thumbs down.", ok: false, fb: "No reason given, so there is nothing to act on." },
            { t: "A thumbs down with: “Draft says replacement cards take 3 to 5 days. KA-2210 says 5 to 7.”", ok: true, fb: "What the draft said, what the source says, and where to look." },
            { t: "Telling a teammate at lunch.", ok: false, fb: "It does not reach the people who can fix the source." },
            { t: "Rewriting it and moving on.", ok: false, fb: "One customer helped. The error is still there for the next contact." }
          ]
        },
        leader: {
          stem: "An agent says: “I tried it in launch week and it was slower.” What is the most useful next move?",
          options: [
            { t: "Walk them through the productivity data.", ok: false, fb: "Data about other people does not answer their own experience." },
            { t: "Sit with them for three live contacts and find where it slows them down.", ok: true, fb: "Observe first. The barrier is usually one specific step you can fix." },
            { t: "Assign the e-learning again.", ok: false, fb: "They completed it once. The gap is in the work, not the course." },
            { t: "Note it and move on.", ok: false, fb: "Launch-week impressions harden if nobody revisits them." }
          ]
        }
      },
      stretch: {
        base: {
          stem: "You found a request that gets excellent dispute summaries. What makes it most valuable?",
          options: [
            { t: "Keeping it to yourself so your numbers stay ahead.", ok: false, fb: "The team's quality is the measure, and it will be found anyway." },
            { t: "Sharing it at the huddle with the case type it works for, so others can reuse and test it.", ok: true, fb: "A named case type makes it reusable, and other people's tests make it better." },
            { t: "Posting it in a chat without context.", ok: false, fb: "Without the case type, people apply it where it does not fit." },
            { t: "Sending it to the vendor.", ok: false, fb: "Your team and the knowledge owners are the right first audience." }
          ]
        },
        leader: {
          stem: "Team usage is high but QA accuracy on AI-assisted contacts is falling. What does that tell you?",
          options: [
            { t: "The rollout is working. Usage is the goal.", ok: false, fb: "Usage is a means. Accuracy is what customers feel." },
            { t: "Adoption without the verify habit. Coach checking before celebrating usage.", ok: true, fb: "High use with falling accuracy is the pattern to catch early." },
            { t: "The tool is broken and should be paused.", ok: false, fb: "Possible, but the first thing to rule out is drafts going out unchecked." },
            { t: "QA is scoring too harshly.", ok: false, fb: "Check a sample before questioning the measure." }
          ]
        }
      },
      explain: {
        base: {
          ask: "Why is reporting a wrong AI draft part of your job, and not only fixing it?",
          ideas: [
            { label: "thinks beyond this one contact", re: "next|other|team|someone else|everyone|again|future|colleague" },
            { label: "connects the report to the fix", re: "fix|improve|update|source|article|tool|correct|better|test" },
            { label: "says to flag it with a reason", re: "flag|report|feedback|reason|tell|raise|why" }
          ],
          model: "Fixing it helps one customer. Flagging it with the reason gets the source corrected, so the error stops reaching every other agent and customer."
        },
        leader: {
          ask: "Why observe live work before coaching an agent on AI use?",
          ideas: [
            { label: "values seeing the real work", re: "see|watch|observ|real|actual|live|side by side|sit with" },
            { label: "looks for the cause, not the symptom", re: "barrier|in the way|slow|why|reason|cause|habit|process|step" },
            { label: "leads to specific coaching", re: "specific|one habit|target|agree|tailor|assum|guess|precise" }
          ],
          model: "The dashboard shows what is happening, not why. Watching real contacts shows the actual barrier, so the coaching targets one specific habit and does not rely on guesses."
        }
      },
      tutor: [
        { q: "What if my feedback gets ignored?", a: "Give it in the form that is hardest to ignore: what the draft said, what the source says, and the article number. Then raise the pattern with your team leader. Specific flags get triaged. Vague ones wait.", ask: "What was the last wrong draft you saw, and could you state it in that form?" },
        { q: "How do I talk to a skeptical teammate?", a: "Start from their experience, not the benefits. Ask what happened when they tried it. One real barrier removed does more than ten statistics.", ask: "Who on your team would you ask first, and what would you ask?" },
        { q: "How do I coach someone who is better at the job than I am with AI?", a: "Ask them to teach it. “Show me how you would use it on this contact” surfaces what they know and where the tool lets them down. Pair them with a newer agent and both improve.", ask: "Who is that person on your team?" }
      ]
    }
  };

  /* General tutor answers, matched by keyword when the learner types a free question in guided mode. */
  var tutorGeneral = [
    { k: ["hallucinat", "make up", "makes up", "invent", "wrong", "mistake", "accura"], a: "Generative AI predicts likely text. Most of the time that is useful. Sometimes it produces a confident sentence that is not true for this account or this policy. That is why every draft gets the ten-second check: numbers, promises, fit." },
    { k: ["replace", "my job", "lose my job", "redundan", "laid off"], a: "In this rollout the assistant drafts and summarizes. The decisions, the customer relationship and the accountability stay with people. The skills in this path, checking, judgment and coaching, are the ones the tool cannot do." },
    { k: ["15", "fifteen", "minute", "short", "how long", "time"], a: "The path is built for fifteen minutes because that fits between contacts or inside a huddle. The diagnostic decides where those minutes go, so you spend them on your gaps and skip what you already do well." },
    { k: ["relay assist", "what is relay", "the tool", "copilot", "assistant do"], a: "Relay Assist is the fictional agent-assist tool in this lab. It drafts replies, summarizes contacts and suggests next steps from the knowledge base. It is a stand-in for whatever approved assistant your team uses." },
    { k: ["prompt", "request", "brief", "ask it"], a: "A good request has four parts: context, task, limits and format. Limits is the one most people skip, and it is the one that stops over-promising." },
    { k: ["pii", "card number", "cvv", "security code", "sensitive", "privacy", "data", "paste"], a: "Minimum necessary. Approved tools only, and even there leave out card numbers, security codes and ID numbers. Describe the case in your own words in place of pasting the record." },
    { k: ["escalat", "hardship", "complain", "vulnerab", "regulator"], a: "Three triggers make it your call: the AI conflicts with policy, the customer shows vulnerability, or the contact is out of pattern, such as a complaint or regulator language. Follow the written procedure, whatever the assistant suggests." },
    { k: ["trust", "rely", "depend", "sure"], a: "Trust the assistant for a first draft. Trust the account screen and the knowledge article for the facts. If they disagree, the source wins and the mismatch gets flagged." },
    { k: ["slow", "faster", "quick", "handle time", "aht"], a: "The time saving comes from a good first draft plus a ten-second check. Skipping the check looks faster until a wrong answer comes back as a repeat contact or a complaint." },
    { k: ["coach", "team", "leader", "huddle", "adopt"], a: "Adoption follows coaching, not announcements. Observe real work, ask before telling, agree one habit, and follow up within a week." },
    { k: ["score", "assess", "grade", "result", "pass"], a: "Your scorecard compares the diagnostic with what you do in the lessons and the simulation. Every score links to the evidence behind it, so you can see exactly which action earned or cost points." }
  ];

  /* ---------- Simulations ---------- */
  var simFrontline = {
    id: "frontline",
    title: { agent: "Live contact: the late fee", backoffice: "Case queue: the late fee" },
    intro: {
      agent: "You are on chat with a cardholder. Relay Assist is open beside the conversation. Every decision here is scored against the five competencies.",
      backoffice: "A secure message has landed in your queue. Relay Assist is open beside the case. Every decision here is scored against the five competencies."
    },
    caseFile: {
      heading: "Case file",
      customer: { agent: "Dana R. · Cardholder since 2019 · Chat", backoffice: "Dana R. · Cardholder since 2019 · Secure message" },
      facts: [
        ["Statement due", "March 3"],
        ["Payment posted", "March 5, $182.40"],
        ["Late fee", "$39, charged March 4"],
        ["Standing", "Good"],
        ["Last courtesy waiver", "14 months ago"]
      ],
      articles: [
        {
          id: "KA-4417", title: "Late fee courtesy waiver",
          lines: [
            "One courtesy waiver per rolling 12 months.",
            "Account in good standing, payment received within 5 days of the due date.",
            "The waiver covers the late fee only. It does not change interest or future fees.",
            "The credit appears within 2 billing cycles.",
            "A second waiver inside 12 months needs team leader approval."
          ]
        },
        {
          id: "KA-5102", title: "Hardship and complaints",
          lines: [
            "Any mention of job loss, illness or inability to pay: offer the Hardship Support referral.",
            "Any request to make a formal complaint: log it in the complaints tool before the contact closes."
          ]
        }
      ]
    },
    stages: [
      {
        id: "s1", type: "choice", comp: { protect: 1 }, label: "Customer shares card details",
        scene: [
          { who: "Dana", text: "I paid on time and you charged me $39 anyway. Here is my card so you can see it is me: 4539 •••• •••• 1127, exp 08/27, code 3••" },
          { who: "note", text: "Shown masked here. Dana typed the full number and security code." }
        ],
        ask: "You were about to ask Relay Assist to summarize the conversation. What do you do?",
        options: [
          { t: "Paste the full conversation into Relay Assist. It is an approved tool.", s: 0, fb: "Approved does not mean unlimited. The assistant does not need a card number to summarize a fee question, and a security code should never be stored anywhere." },
          { t: "Ask Dana not to share card details here, verify through the standard steps, start the redaction step, and keep those details out of your prompt.", s: 1, fb: "Minimum necessary. You verified through the proper route, protected the customer, and kept the details out of the AI tool." },
          { t: "Say nothing about it. Keep the card details out of your prompt and carry on.", s: 0.5, fb: "Keeping it out of the prompt matters. But the unredacted number is still in the transcript, and Dana will do it again." },
          { t: "Copy the conversation into a personal AI app. It summarizes faster.", s: 0, fb: "Customer data never goes into a tool that is not approved. This one is a reportable incident." }
        ],
        hint: "Two questions: does the assistant need this detail to do the task, and what should happen to sensitive data already in the transcript?"
      },
      {
        id: "s2", type: "prompt", comp: { prompt: 1 }, label: "Brief Relay Assist",
        scene: [{ who: "note", text: "Dana is verified. You want a first draft of the reply." }],
        ask: "Write the request you would give Relay Assist. Use the case file.",
        placeholder: "Type your request to Relay Assist…",
        criteria: [
          { id: "context", label: "Context", re: "(late|fee|\\$ ?39).*(posted|2 days|two days|after|late|good standing|12 months|14 months|waiver)|(posted|2 days|two days|good standing|12 months|14 months).*(fee|late)", tip: "Add the facts that change the answer: payment posted two days late, good standing, no waiver in 12 months." },
          { id: "task", label: "Task", re: "draft|write|reply|respond|response|message|compose", tip: "Say what you want produced, such as a chat reply." },
          { id: "limits", label: "Limits", re: "ka-? ?4417|knowledge article|polic|only|do not|don't|dont|no promis|never|must not|avoid|stay within|stick to|without promis", tip: "Tell it what it must not promise. Naming KA-4417 does this in three words." },
          { id: "format", label: "Format", re: "short|brief|under \\d+|\\d+ words|sentence|warm|empath|plain|friendly|tone|concise|polite|apolog", tip: "Give a length and a tone." }
        ],
        model: "Customer disputes a $39 late fee. Payment posted 2 days after the due date. Account in good standing, last courtesy waiver 14 months ago. Draft a chat reply applying the courtesy waiver. Stay within KA-4417: fee only, no promises about interest or future fees. Under 90 words, warm, plain language.",
        hint: "Four parts: context, task, limits, format. The case file has every fact you need. The customer's card number is not one of them."
      },
      {
        id: "s3", type: "flag", comp: { verify: 1 }, label: "Check the draft",
        scene: [{ who: "note", text: "Relay Assist returned this draft." }],
        ask: "Select every sentence you would change before sending. Check each one against the case file.",
        segments: [
          { t: "Hi Dana, thanks for getting in touch, and I am sorry for the stress this fee has caused.", bad: false },
          { t: "I can see your payment was received on time.", bad: true, why: "Numbers. The payment posted March 5, two days after the due date." },
          { t: "Because your account is in good standing and you have not had a courtesy waiver in the last 12 months, I have removed the $39 late fee.", bad: false },
          { t: "I have also refunded the interest charged this month.", bad: true, why: "Promises. KA-4417 covers the late fee only." },
          { t: "You will see the credit within two billing cycles.", bad: false },
          { t: "Going forward, any late fees on your account will be waived automatically.", bad: true, why: "Promises. One waiver per 12 months. This cannot be delivered." },
          { t: "Is there anything else I can help you with today?", bad: false }
        ],
        hint: "Run the ten-second check on each sentence: numbers against the account, promises against KA-4417."
      },
      {
        id: "s4", type: "choice", comp: { judge: 1 }, label: "The contact changes",
        scene: [
          { who: "Dana", text: "Thank you. This is the third time a payment has posted late on your side and I want to make a formal complaint. I lost my job in January and I am struggling to keep up." },
          { who: "assist", text: "Next best action: confirm the waiver and close the contact." }
        ],
        ask: "What do you do?",
        options: [
          { t: "Follow the suggestion. The fee is resolved and handle time is already long.", s: 0, fb: "The fee was only part of what Dana said. Two triggers in KA-5102 were missed: a formal complaint and a hardship signal." },
          { t: "Log the formal complaint, offer the Hardship Support referral, then confirm the waiver. Treat the suggestion as incomplete.", s: 1, fb: "Both triggers handled by the written procedure. The assistant matched the fee pattern and missed the person." },
          { t: "Ask Relay Assist whether this counts as hardship, and follow its answer.", s: 0, fb: "The trigger is written in KA-5102. You do not need the assistant's permission to follow it, and it cannot be accountable for the outcome." },
          { t: "Offer the Hardship Support referral and close. The complaint was about the fee, which is fixed.", s: 0.5, fb: "Hardship handled well. But Dana asked to make a formal complaint, and that must be logged whether or not the fee is fixed." }
        ],
        hint: "Read Dana's message again against KA-5102. How many triggers are in it?"
      },
      {
        id: "s5", type: "choice", comp: { improve: 1 }, label: "After the contact",
        scene: [{ who: "note", text: "The contact is closed. The draft from Relay Assist contained three errors." }],
        ask: "What do you do next?",
        options: [
          { t: "Nothing. The errors were caught, so no harm done.", s: 0, fb: "You caught them. The next person might not. Unreported errors stay in the tool." },
          { t: "Flag the draft with the reason using the feedback control, and raise the pattern at the team huddle.", s: 1, fb: "This is how the tool and the training improve. Your flag becomes a test case for the next release." },
          { t: "Stop using Relay Assist on fee contacts.", s: 0, fb: "Avoiding the tool hides the problem and gives up the time saved where it works." },
          { t: "Message a couple of teammates to watch out for it.", s: 0.5, fb: "Useful for those teammates. It does not reach the people who can fix the source." }
        ],
        hint: "Who can fix the source of the error, and what do they need from you to do it?"
      }
    ]
  };

  var simLeader = {
    id: "leader",
    title: { leader: "Week four: coach through the dip" },
    intro: { leader: "You lead 14 agents. Relay Assist launched four weeks ago. You have 30 minutes of coaching time today. Every decision here is scored against the five competencies." },
    caseFile: {
      heading: "Team snapshot",
      customer: { leader: "Your team · 14 agents · Rollout week 4" },
      facts: [
        ["Contacts using Relay Assist", "46% (site average 63%)"],
        ["QA this week", "3 contacts with an AI draft sent unedited, each with a policy error"],
        ["All three from", "Marcus T., your highest user"],
        ["Not using it", "Priya N., 6 years in role, top-quartile QA"],
        ["Handle time", "Down 9% since launch"]
      ],
      articles: [
        {
          id: "CG-12", title: "Coaching guide",
          lines: [
            "Observe the work before you discuss it.",
            "Ask before telling.",
            "Agree one specific habit.",
            "Follow up within a week, on real contacts."
          ]
        },
        {
          id: "AI-03", title: "Approved tools",
          lines: [
            "Customer information goes only into approved tools.",
            "Never paste account details or customer messages into a public AI app.",
            "If it happens, report it through the incident process the same day."
          ]
        }
      ]
    },
    stages: [
      {
        id: "l1", type: "choice", comp: { judge: 1 }, label: "Where to start",
        scene: [{ who: "note", text: "Two people need your time. You can see one properly today." }],
        ask: "Where do you start?",
        options: [
          { t: "Email the team a reminder to use Relay Assist, with the launch training attached.", s: 0, fb: "Reminders do not change habits, and the QA errors go untouched." },
          { t: "Marcus. Unedited drafts with policy errors are reaching customers now.", s: 1, fb: "Customer impact sets the order. Low usage is a slow problem. Wrong information sent to customers is today's problem." },
          { t: "Priya. She is the biggest adoption gap.", s: 0.5, fb: "Worth doing this week. But Priya's customers are getting accurate answers. Marcus's are not." },
          { t: "Set a team target of 70% usage by Friday.", s: 0, fb: "A usage target with no quality check rewards exactly what Marcus is doing." }
        ],
        hint: "Which of the two situations is affecting customers right now?"
      },
      {
        id: "l2", type: "choice", comp: { improve: 1 }, label: "Open the conversation",
        scene: [{ who: "note", text: "You sit down with Marcus." }],
        ask: "How do you open?",
        options: [
          { t: "“Three of your contacts failed QA this week. That cannot happen again.”", s: 0, fb: "Accurate, and it shuts the conversation down. You get compliance while you are watching and nothing after." },
          { t: "“Pull up one of this week's fee contacts and walk me through how you decided the draft was ready to send.”", s: 1, fb: "Observe, then ask. You see his real process, and he finds the gap himself." },
          { t: "“Your usage is the best on the team. Keep it up.”", s: 0, fb: "True, and it avoids the reason you are here." },
          { t: "“I am moving you back to manual drafting until QA improves.”", s: 0, fb: "It removes the risk and the learning. He is your most willing adopter." }
        ],
        hint: "CG-12 gives the order: observe, ask, agree, follow up."
      },
      {
        id: "l3", type: "choice", comp: { verify: 1 }, label: "The pushback",
        scene: [{ who: "Marcus", text: "The drafts are right nearly every time. Checking each one eats the time I am saving." }],
        ask: "What do you do?",
        options: [
          { t: "Agree one habit: before sending, check every amount, date and promise against the account and the article. Review three contacts together next week.", s: 1, fb: "Specific, quick to do, and it has a follow-up. This is the ten-second check turned into a habit." },
          { t: "Tell him to read every draft twice.", s: 0.5, fb: "More checking, but not targeted. Reading twice does not tell him what to look for." },
          { t: "Tell him to stop using Relay Assist on fee contacts.", s: 0, fb: "It gives up the benefit and teaches the team that mistakes get the tool taken away." },
          { t: "Accept it. His handle time is the best on the team.", s: 0, fb: "Handle time falling while accuracy falls is not readiness." }
        ],
        hint: "What would a check look like that takes ten seconds and targets where the errors were?"
      },
      {
        id: "l4", type: "prompt", comp: { prompt: 1 }, label: "Prepare for Priya",
        scene: [{ who: "note", text: "Priya is next. You want help preparing, using your approved assistant." }],
        ask: "Write the request you would give the assistant to help you prepare for the conversation with Priya.",
        placeholder: "Type your request to the assistant…",
        criteria: [
          { id: "context", label: "Context", re: "experienc|tenure|6 years|six years|senior|top|strong qa|high qa|has not|hasn't|not us|not open|stopped|slow|skeptic|sceptic|relucta|launch", tip: "Describe the situation: an experienced, high-quality agent who has not used the tool since launch week." },
          { id: "task", label: "Task", re: "prepare|plan|question|coach|conversation|draft|outline|agenda|suggest|help me", tip: "Say what you want: questions to ask, or a plan for the conversation." },
          { id: "limits", label: "Limits", re: "do not|don't|dont|avoid|no |not a script|without|open question|not tell|rather than tell|ask before|non-?judg|no pressure|no target", tip: "Set limits: open questions, no script, no usage targets." },
          { id: "format", label: "Format", re: "bullet|list|short|\\d+ (question|minute|point)|five|three|four|one page|step|brief|concise", tip: "Give a format, such as five questions for a 15-minute conversation." }
        ],
        nameCheck: "priya",
        model: "I lead a contact center team four weeks into an AI assistant rollout. One experienced agent with top-quartile quality has not used the tool since launch week and says it slows her down. Help me prepare a 15-minute coaching conversation. Give me five open questions that explore what gets in her way. No script, no usage targets, nothing that sounds like a performance warning. Bullets.",
        hint: "Context, task, limits, format. You can describe the situation without naming the person."
      },
      {
        id: "l5", type: "choice", comp: { protect: 1 }, label: "An honest admission",
        scene: [{ who: "Priya", text: "Honestly, I draft faster with the AI app on my phone. I paste the customer's message in and tidy up what comes back." }],
        ask: "What do you do?",
        options: [
          { t: "Thank her for telling you, stop the practice today, explain why, report it through the incident process, and show her the same steps in Relay Assist.", s: 1, fb: "Stop, explain, report, replace. Reporting protects Priya as well as the customer, and she leaves with a way to keep the speed." },
          { t: "Tell her to stop, and leave it there. She meant well.", s: 0.5, fb: "Stopping it is right. But customer data has already left approved systems, and AI-03 requires a report the same day." },
          { t: "Let it go. Her quality scores are excellent.", s: 0, fb: "Good outcomes do not make an unapproved tool acceptable. The exposure is the issue." },
          { t: "Ask which app it is so the rest of the team can try it.", s: 0, fb: "That spreads the exposure across the team." }
        ],
        hint: "AI-03 has three lines. Which ones apply to what Priya just said?"
      },
      {
        id: "l6", type: "choice", comp: { improve: 1 }, label: "Report readiness",
        scene: [{ who: "Ops manager", text: "Quick one before the review. Is your team ready?" }],
        ask: "What do you bring?",
        options: [
          { t: "Usage: 46% of contacts, up from 31%.", s: 0.5, fb: "Usage shows the tool is being opened. It does not show whether customers are getting better answers." },
          { t: "Usage, QA accuracy on AI-assisted contacts, what agents say gets in the way, and the two habits you are coaching this week.", s: 1, fb: "Adoption, quality, barriers and action. That is a readiness picture a manager can act on." },
          { t: "Nothing yet. Wait until the numbers look better.", s: 0, fb: "Early, honest numbers get you help. Late good news gets you questions." },
          { t: "Handle time is down 9%.", s: 0.5, fb: "Worth reporting, alongside quality. Speed without accuracy is not readiness." }
        ],
        hint: "Readiness has more than one measure. What would tell her that customers are better off?"
      }
    ]
  };

  /* ---------- Coaching content ---------- */
  var practice = {
    prompt: {
      rep: { base: "On your next five contacts, write the request in four parts before you send it. Count how many first drafts you could use with light edits.", leader: "Review five requests your agents wrote this week. For each one, name the missing part and show the rewrite." },
      leaderAsk: ["Show me the last request you gave the assistant. Which of the four parts is in it?", "What happened to the draft when you added limits?", "Which contact type gives you the weakest drafts?"],
      huddle: "Put one weak request on screen. Ask the team to name the missing part, then rewrite it together in under two minutes."
    },
    verify: {
      rep: { base: "On your next five AI drafts, say the check out loud or in your head: numbers, promises, fit. Note every correction you make.", leader: "Pull three AI-assisted contacts from QA this week. Walk through numbers, promises and fit with the agent who handled each one." },
      leaderAsk: ["Walk me through how you decided this draft was ready to send.", "What did you check it against?", "What would have happened if this sentence had gone out as written?"],
      huddle: "Show one real draft with a planted error. First person to find it explains which check caught it."
    },
    protect: {
      rep: { base: "For one shift, before each request to the assistant, ask: does it need this detail to do the task? Describe the case in your own words.", leader: "Run the needed-or-not drill in this week's huddle, and check that every agent knows where the incident form is." },
      leaderAsk: ["What did you leave out of that request, and why?", "What would you do if a customer typed a card number into chat?", "Where is the incident form, and when would you use it?"],
      huddle: "Read out three details from a case. For each one the team answers: needed in the prompt, or not?"
    },
    judge: {
      rep: { base: "For one shift, note every contact where one of the three triggers appeared: conflict, vulnerability, out of pattern. Bring one to your next one-to-one.", leader: "Ask each agent for one contact this week where they did not follow the AI suggestion. Talk through which trigger it was." },
      leaderAsk: ["Tell me about a contact this week where you did not follow the suggestion.", "Which trigger was it?", "What would make it easier to escalate when you are unsure?"],
      huddle: "Read a customer message aloud. The team calls out the trigger and the procedure it leads to."
    },
    improve: {
      rep: { base: "Flag at least two drafts this week with a reason that names what the draft said and what the source says.", leader: "Sit with two agents for three live contacts each this week. Ask before telling, agree one habit with each, and book the follow-up." },
      leaderAsk: ["What is the last thing you flagged, and what happened to it?", "What gets in your way when you use the tool?", "What is one thing that works that the team should know about?"],
      huddle: "Each person shares one request that worked and the contact type it worked for. Capture them in the team notes."
    }
  };

  var coachSteps = [
    { id: "goal", label: "Goal", ask: function (c) { return "Your priority area is “" + c.name + "”. What would good look like on your next shift?"; }, reflect: "That is specific enough to notice when it happens." },
    { id: "reality", label: "Reality", ask: function () { return "What happens today that gets in the way of that?"; }, reflect: "Naming the barrier is most of the work. It is usually one step, not the whole job." },
    { id: "options", label: "Options", ask: function () { return "What is one small thing you could try on your next five contacts?"; }, reflect: "Small and countable. That is what makes it likely to happen." },
    { id: "will", label: "Commitment", ask: function () { return "Who will you tell, and when will you check how it went?"; }, reflect: "A named person and a date turn an intention into a plan." }
  ];

  /* ---------- Synthetic adoption data: 12 weeks, 5 sites, 3 roles ---------- */
  var sites = [
    { id: "harbor", name: "Harbor Point", rate: 0.34, cap: 0.93, skill: 4 },
    { id: "lakeside", name: "Lakeside", rate: 0.3, cap: 0.9, skill: 2 },
    { id: "ridgeview", name: "Ridgeview", rate: 0.2, cap: 0.82, skill: -5 },
    { id: "southgate", name: "Southgate", rate: 0.26, cap: 0.88, skill: 0 },
    { id: "virtual", name: "Virtual team", rate: 0.23, cap: 0.86, skill: -2 }
  ];
  var cohortRoles = [
    { id: "agent", name: "Contact center agents", share: 0.65, lift: 1 },
    { id: "backoffice", name: "Back-office specialists", share: 0.26, lift: 0.88 },
    { id: "leader", name: "Team leaders", share: 0.09, lift: 1.08 }
  ];
  var headcount = { harbor: 620, lakeside: 540, ridgeview: 460, southgate: 430, virtual: 350 };

  function buildCohorts() {
    var out = [];
    sites.forEach(function (s, si) {
      cohortRoles.forEach(function (r, ri) {
        var n = Math.round(headcount[s.id] * r.share);
        var weeks = [];
        for (var w = 1; w <= 12; w++) {
          var wobble = Math.sin((w + si * 2 + ri) * 1.3) * 0.012;
          var activated = Math.min(s.cap, s.cap * (1 - Math.exp(-s.rate * 1.25 * w)) + wobble);
          var completed = activated * Math.min(0.94, 0.55 + 0.035 * w) * r.lift;
          var active = completed * Math.min(0.9, 0.5 + 0.034 * w + wobble * 2) * r.lift;
          var proficient = completed * Math.min(0.8, 0.12 + 0.052 * w) * r.lift;
          weeks.push({
            w: w,
            activated: Math.round(n * Math.min(1, activated)),
            completed: Math.round(n * Math.min(1, completed)),
            active: Math.round(n * Math.min(1, active)),
            proficient: Math.round(n * Math.min(1, proficient))
          });
        }
        var comp = {};
        var base = { prompt: 78, verify: 71, protect: 84, judge: 74, improve: 66 };
        Object.keys(base).forEach(function (k, ki) {
          var adj = s.skill + (r.id === "leader" ? (k === "improve" ? 9 : 2) : 0) + (r.id === "backoffice" ? (k === "protect" ? 3 : -2) : 0);
          comp[k] = Math.max(40, Math.min(96, base[k] + adj + ((si * 3 + ki * 5 + ri) % 5) - 2));
        });
        out.push({ site: s.id, role: r.id, n: n, weeks: weeks, comp: comp, daysToProficient: Math.round(31 - s.skill * 0.9 + (r.id === "backoffice" ? 4 : 0)) });
      });
    });
    return out;
  }

  var outcomes = [
    { metric: "QA accuracy on AI-assisted contacts", before: 91.2, after: 96.4, dp: 1, suffix: "%", dUnit: " pts", better: "up" },
    { metric: "Average handle time", before: 412, after: 371, dp: 0, suffix: " sec", dUnit: " sec", better: "down" },
    { metric: "First-contact resolution", before: 71.0, after: 75.8, dp: 1, suffix: "%", dUnit: " pts", better: "up" },
    { metric: "Escalations routed correctly", before: 83.1, after: 90.6, dp: 1, suffix: "%", dUnit: " pts", better: "up" },
    { metric: "Agent confidence with the tool, 1 to 5", before: 2.9, after: 4.1, dp: 1, suffix: "", dUnit: "", better: "up" },
    { metric: "Complaints per 1,000 contacts", before: 4.1, after: 3.4, dp: 1, suffix: "", dUnit: "", better: "down" }
  ];

  var teams = [
    { team: "Ridgeview 7", site: "ridgeview", lead: "T. Okafor", use: 31, qa: 89.4, signal: "Low use, low confidence", status: "crit", play: "Leader sits side by side for three live contacts per agent, then one habit each." },
    { team: "Virtual 3", site: "virtual", lead: "M. Alvarez", use: 74, qa: 88.1, signal: "High use, accuracy falling", status: "crit", play: "Run the verify huddle. QA samples AI-assisted contacts for two weeks." },
    { team: "Southgate 2", site: "southgate", lead: "J. Brandt", use: 44, qa: 95.9, signal: "Strong quality, slow adoption", status: "warn", play: "Pair the two most experienced agents with daily users for a week." },
    { team: "Ridgeview 4", site: "ridgeview", lead: "S. Lindqvist", use: 39, qa: 93.0, signal: "Leader has not completed coaching sprint", status: "warn", play: "Leader completes the coaching sprint, then a peer leader shadows one huddle." },
    { team: "Lakeside 9", site: "lakeside", lead: "R. Chen", use: 58, qa: 94.2, signal: "Three unapproved-tool reports", status: "warn", play: "Protect sprint for the whole team. Show the approved route for the same task." },
    { team: "Harbor Point 5", site: "harbor", lead: "A. Mensah", use: 83, qa: 97.6, signal: "Exemplar team", status: "good", play: "Capture their requests library and share it across sites." }
  ];

  var experiments = [
    { name: "15-minute sprints vs one 60-minute class", result: "Completion 81% vs 54%. Proficiency at day 30: 62% vs 47%.", decision: "Adopted sprints as the default format.", n: "640 associates, 2 sites" },
    { name: "Leader-led huddle after each sprint", result: "Weekly use on live contacts 71% vs 58% without a huddle.", decision: "Added a five-minute huddle script to every sprint.", n: "38 teams" },
    { name: "Nudge at shift start vs after first break", result: "Sprint starts 44% vs 61%.", decision: "Moved the nudge to after first break.", n: "1,120 associates" }
  ];

  /* ---------- Blueprint content ---------- */
  var traceability = [
    { need: "Design and implement a training, change management and adoption agenda for AI in daily work", here: "The whole path: diagnose, learn, apply, measure, coach", scale: "One sprint template reused across contact types and sites" },
    { need: "Operational AI readiness for call center agents, back-office agents and frontline leaders", here: "Three role lenses change the scenarios, the simulation and the coaching", scale: "Role packs maintained with operations subject experts" },
    { need: "Coaching toolkits and change enablement resources for team leaders", here: "Leader simulation, conversation guides, huddle scripts and a commitment card", scale: "Toolkits delivered with each sprint and tied to team-level data" },
    { need: "Align AI enablement with business OKRs and governance", here: "Adoption analytics pairs usage with quality, escalation and complaint measures", scale: "Readiness scorecard reviewed with accountable executives each month" },
    { need: "Reuse scalable enterprise assets while tailoring for the frontline", here: "Five shared competencies, with frontline scenarios layered on top", scale: "Enterprise AI fluency content as the base, operations cases as the wrapper" },
    { need: "Iteration, experimentation and continuous feedback loops", here: "Experiment log, learner flags and evidence-linked scoring", scale: "Monthly content release driven by flags, QA findings and test results" },
    { need: "AI fluency and prompt engineering concepts", here: "Scored prompt-writing task, AI tutor, draft verification exercise", scale: "Prompt patterns library owned jointly with the tool's product team" }
  ];

  var plan = [
    { when: "Days 1 to 30", title: "Listen and baseline", items: ["Shadow agents and leaders at two sites", "Agree readiness measures with operations and risk", "Baseline the five competencies with a short diagnostic", "Review existing enterprise AI learning assets for reuse"] },
    { when: "Days 31 to 60", title: "Pilot and learn", items: ["Pilot three sprints with four teams", "Train leaders on the coaching loop before their teams start", "Run two format experiments", "Stand up the readiness scorecard"] },
    { when: "Days 61 to 90", title: "Scale what worked", items: ["Roll out by site in waves, leaders first", "Monthly content release from flags and QA findings", "Report adoption with quality, never usage alone", "Hand exemplar teams a requests library to share"] }
  ];

  var governance = [
    ["Human in the loop", "AI drafts and suggests. A person decides and is accountable for what is sent."],
    ["Approved tools only", "Learning content never asks for customer data. Simulations use invented cases."],
    ["Tested before release", "Tutor and simulation answers get tested against source policy before each release, including cases where written guidance conflicts."],
    ["Transparent scoring", "Rule-based rubrics, with the evidence shown to the learner. AI adds commentary, never the score."],
    ["Accessible by design", "Keyboard operable, readable at phone width, light and dark themes, plain language."],
    ["Privacy of learner data", "Individual results go to the learner and their leader. Executives see cohorts."]
  ];

  var measures = [
    ["Reaction", "Was it worth the time?", "Sprint rating, completion, drop-off point"],
    ["Learning", "Can they do it here?", "Pre and post competency scores, simulation results"],
    ["Behavior", "Do they do it on live work?", "Weekly use on contacts, flags raised, QA on AI-assisted contacts"],
    ["Results", "Is the business better off?", "Accuracy, handle time, first-contact resolution, complaints"]
  ];

  var about = {
    name: "Vincent Gibson",
    line: "Operations leader in workforce learning, change management and applied generative AI",
    linkedin: "https://www.linkedin.com/in/vincent-g-098b6741",
    points: [
      ["Adaptive AI tutoring", "Designed a generative AI tutor prompt that offers a 15-minute learning option, adapts examples to the learner\u2019s experience, checks understanding and asks learners to explain or apply what they learned."],
      ["Tested AI guidance", "Co-developed a donation-workflow assistant and a policy chatbot for the CARITAS Furniture Bank team practicum. All 12 test cases passed, including escalation when written guidance conflicted."],
      ["Coaching that moved numbers", "Introduced manager coaching and peer-led training in a 50-person division. Internal customer satisfaction rose from 43% to 69% and turnover fell 87%."],
      ["Change at scale", "Aligned six newly reorganized divisions with more than 150 staff, using one-to-one conversations and weekly 30-minute check-ins."],
      ["Credentials", "Georgetown Certificate in Leadership Coaching. M.S. Business Analytics and M.S. Management of IT, University of Virginia. Six Sigma Black Belt."]
    ]
  };

  window.LAB = {
    competencies: competencies, roles: roles, experience: experience, roleWeights: roleWeights,
    diagnostic: diagnostic, lessons: lessons, tutorGeneral: tutorGeneral,
    sims: { frontline: simFrontline, leader: simLeader },
    practice: practice, coachSteps: coachSteps,
    sites: sites, cohortRoles: cohortRoles, cohorts: buildCohorts(),
    outcomes: outcomes, teams: teams, experiments: experiments,
    traceability: traceability, plan: plan, governance: governance, measures: measures, about: about
  };
})();
