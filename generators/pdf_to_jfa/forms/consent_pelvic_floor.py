"""
Layout for: Consent for Pelvic Floor Muscle Evaluation and Treatment (Doc 4023I)

Source PDF: Form_4023I_Client_Consent_Invasive_Procedure__Pelvic_Floor_.pdf
Page: A4 portrait (595.32 x 841.92 pts)
Concept: z..UB ("Consent for Pelvic Floor Muscle Evaluation and Treatment")
Folder: Consent Forms

Strategy: Option 1 (text rebuilt as labels) for body content; Option 2 (image
overlay) for the NWRH logo only. Header table is drawn as labels.

Deliberately omitted from the CDO version:
  - The page-number "1" at the bottom of the printed form.
  - The underscore fill-lines after each field label — these are replaced by
    actual TICDOEdit / TICDOSignature / TICDODateEdit controls, so the labels
    read simply "Client Name:", "Client Signature:", "Date:", etc.

Known visual divergence from the printed form:
  - "Potential Benefits" and "Potential risks" lead-ins are rendered in the
    same weight as the surrounding text rather than bold. DFM TICDOLabel does
    not support inline bold runs within a single caption.
"""
from __future__ import annotations
from ..layout import FormLayout, Rect, Label, Edit, DateEdit, Signature, Image


PARAGRAPHS = [
    ("lblP1",
     "Informed consent means that the potential risks, benefits and "
     "alternatives of therapy evaluation and treatment have been explained to you."),

    ("lblP2",
     "I also acknowledge and understand that I have been referred for "
     "evaluation and treatment of pelvic floor dysfunction. Pelvic floor "
     "dysfunctions include but not limited to urinary or faecal incontinence."),

    ("lblP3",
     "I understand that to evaluate my condition it may be necessary, "
     "initially and periodically, to have my Continence Nurse perform an "
     "internal pelvic floor muscle examination."),

    ("lblP4",
     "The examination is performed by observing and /or palpating the "
     "perineal region including vagina and /or rectum. This evaluation will "
     "assess skin condition, reflexes, muscle tone, length, strength and "
     "endurance, scar mobility and function of pelvic floor region. I will "
     "have the opportunity to give/revoke my consent at/during each "
     "treatment session."),

    ("lblP5",
     "Due to the private nature of the condition and examination, we "
     "encourage you to ask as many questions as you need to increase your "
     "comfort and understanding of your evaluation, any findings, and the treatment."),

    ("lblP6",
     "Potential Benefits: may include an improvement in my symptoms and "
     "increase my ability to perform my daily activities. I may experience "
     "increase strength, awareness, flexibility and endurance in my movements. "
     "I shall gain greater knowledge about managing my condition and resources "
     "available to me."),

    ("lblP7",
     "Potential risks: I may experience a level of pain or discomfort or an "
     "aggravation of my existing injury. The discomfort is usually temporary, "
     "if it does not subside in 1-3 days, I agree to contact my Continence Advisor."),

    ("lblP8",
     "If you consent, you have the option to have a second person (chaperone) "
     "in the room for the pelvic floor muscle evaluation and treatment. The "
     "second person may be a friend, family member, or other clinical staff "
     "member. Please indicate to your Continence Nurse if you wish to proceed "
     "with a chaperone."),

    ("lblP9",
     "I have informed my Continence Advisor of any condition that would limit "
     "my ability to have an evaluation or be treated. I hereby request consent "
     "to the evaluation and treatment to be provided."),
]


def _estimate_paragraph_height_pt(text: str, font_size_pt: int, body_width_pt: float) -> float:
    """Conservative height estimate for a wrapped paragraph in TICDOLabel."""
    avg_char_w_factor = 0.58
    line_height_factor = 1.4
    avg_char_w = font_size_pt * avg_char_w_factor
    line_height = font_size_pt * line_height_factor
    chars_per_line = max(20, int(body_width_pt / avg_char_w))
    words = text.split()
    lines = 1
    cur = 0
    for w in words:
        if cur == 0:
            cur = len(w)
        elif cur + 1 + len(w) <= chars_per_line:
            cur += 1 + len(w)
        else:
            lines += 1
            cur = len(w)
    return lines * line_height + 6


def build_layout(logo_image_path: str, form_def_id: int = 90000100) -> FormLayout:
    """Construct the FormLayout for this consent form."""
    layout = FormLayout(
        form_name='ConsentPelvicFloorEval',
        caption='Consent for Pelvic Floor Muscle Evaluation and Treatment',
        page_width_pt=595.32,
        page_height_pt=841.92,
        concept_code='z..UB',
        concept_display_name='Consent for Pelvic Floor Muscle Evaluation and Treatment',
        folder_category='Consent Forms',
        form_def_id=form_def_id,
    )

    # Header table
    HDR_X1, HDR_X2 = 35, 130
    HDR_W1, HDR_W2 = 90, 90
    HDR_Y0, HDR_RH = 33, 16

    layout.add(Label(name='lblHdrDocLabel',    rect=Rect(HDR_X1, HDR_Y0 + 0*HDR_RH, HDR_W1, HDR_RH),
                     text='Document No.', font_size=9, word_wrap=False, auto_size=False))
    layout.add(Label(name='lblHdrDocValue',    rect=Rect(HDR_X2, HDR_Y0 + 0*HDR_RH, HDR_W2, HDR_RH),
                     text='4023I', font_size=9, word_wrap=False, auto_size=False))
    layout.add(Label(name='lblHdrRevLabel',    rect=Rect(HDR_X1, HDR_Y0 + 1*HDR_RH, HDR_W1, HDR_RH),
                     text='Revision No.', font_size=9, word_wrap=False, auto_size=False))
    layout.add(Label(name='lblHdrRevValue',    rect=Rect(HDR_X2, HDR_Y0 + 1*HDR_RH, HDR_W2, HDR_RH),
                     text='1.1', font_size=9, word_wrap=False, auto_size=False))
    layout.add(Label(name='lblHdrReviewLabel', rect=Rect(HDR_X1, HDR_Y0 + 2*HDR_RH, HDR_W1, HDR_RH),
                     text='Review Date', font_size=9, word_wrap=False, auto_size=False))
    layout.add(Label(name='lblHdrReviewValue', rect=Rect(HDR_X2, HDR_Y0 + 2*HDR_RH, HDR_W2, HDR_RH),
                     text='20 Aug 26', font_size=9, word_wrap=False, auto_size=False))
    layout.add(Label(name='lblHdrPageLabel',   rect=Rect(HDR_X1, HDR_Y0 + 3*HDR_RH, HDR_W1, HDR_RH),
                     text='Page No.', font_size=9, word_wrap=False, auto_size=False))
    layout.add(Label(name='lblHdrPageValue',   rect=Rect(HDR_X2, HDR_Y0 + 3*HDR_RH, HDR_W2, HDR_RH),
                     text='1 of 1', font_size=9, word_wrap=False, auto_size=False))

    layout.add(Label(name='lblFormTitle',
                     rect=Rect(240, 38, 230, 50),
                     text='Consent for Pelvic Floor Muscle\nEvaluation and Treatment',
                     font_size=12, bold=True, word_wrap=True, auto_size=False))

    layout.add(Image(name='imgNwrhLogo',
                     rect=Rect(481, 30, 79, 60),
                     image_path=logo_image_path,
                     stretch=True, proportional=True))

    # Body paragraphs flow from a fixed start, allocated estimated heights.
    BODY_X = 35
    BODY_W = 525
    PARA_FONT = 10
    PARA_GAP = 10
    BODY_Y_START = 105

    cur_y = BODY_Y_START
    for name, text in PARAGRAPHS:
        h = _estimate_paragraph_height_pt(text, PARA_FONT, BODY_W)
        layout.add(Label(name=name,
                         rect=Rect(BODY_X, cur_y, BODY_W, h),
                         text=text, font_size=PARA_FONT,
                         word_wrap=True, auto_size=False))
        cur_y += h + PARA_GAP

    # Field controls anchored below the body.
    FIELD_BLOCK_Y = max(cur_y + 12, 515)
    ROW_GAP = 28
    FIELD_H = 18
    LBL_FONT = 10

    def _add_name_row(prefix, y, label_text, label_w, hri, tab):
        layout.add(Label(name=f'lbl{prefix}NameLabel',
                         rect=Rect(BODY_X, y, label_w, 14),
                         text=label_text, font_size=LBL_FONT,
                         word_wrap=False, auto_size=False))
        layout.add(Edit(name=f'edt{prefix}Name',
                        rect=Rect(BODY_X + label_w + 3, y - 2,
                                  BODY_W - label_w - 5, FIELD_H),
                        hri=hri, label=label_text.rstrip(':').strip(),
                        tab_order=tab))

    def _add_sig_date_row(prefix, y, sig_label, sig_label_w, sig_end_x,
                          date_label_w, sig_hri, date_hri, tab_sig, tab_date):
        layout.add(Label(name=f'lbl{prefix}SigLabel',
                         rect=Rect(BODY_X, y, sig_label_w, 14),
                         text=sig_label, font_size=LBL_FONT,
                         word_wrap=False, auto_size=False))
        sig_x = BODY_X + sig_label_w + 3
        sig_w = sig_end_x - sig_x - date_label_w - 3
        layout.add(Signature(name=f'sig{prefix}',
                             rect=Rect(sig_x, y - 2, sig_w, FIELD_H),
                             hri=sig_hri,
                             label=sig_label.rstrip(':').strip(),
                             tab_order=tab_sig))
        date_label_x = sig_end_x - date_label_w
        layout.add(Label(name=f'lbl{prefix}DateLabel',
                         rect=Rect(date_label_x, y, date_label_w, 14),
                         text='Date:', font_size=LBL_FONT,
                         word_wrap=False, auto_size=False))
        date_x = date_label_x + date_label_w + 3
        date_w = (BODY_X + BODY_W) - date_x
        layout.add(DateEdit(name=f'dte{prefix}',
                            rect=Rect(date_x, y - 2, date_w, FIELD_H),
                            hri=date_hri,
                            label=f'{prefix} Date',
                            tab_order=tab_date))

    y = FIELD_BLOCK_Y
    _add_name_row('Client', y, 'Client Name:', 65, hri=1001, tab=0)
    y += ROW_GAP
    _add_sig_date_row('Client', y, 'Client Signature:', 85, 415, 32,
                      sig_hri=1002, date_hri=1003, tab_sig=1, tab_date=2)
    y += ROW_GAP
    _add_name_row('Chaperone', y, 'Chaperone Name:', 90, hri=1004, tab=3)
    y += ROW_GAP
    _add_sig_date_row('Chaperone', y, 'Chaperone Signature:', 110, 423, 32,
                      sig_hri=1005, date_hri=1006, tab_sig=4, tab_date=5)
    y += ROW_GAP
    _add_name_row('Clinician', y, 'Clinician Name:', 80, hri=1007, tab=6)
    y += ROW_GAP
    _add_sig_date_row('Clinician', y, 'Clinician Signature:', 100, 422, 32,
                      sig_hri=1008, date_hri=1009, tab_sig=7, tab_date=8)

    return layout
