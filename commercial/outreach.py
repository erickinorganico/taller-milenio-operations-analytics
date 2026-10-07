"""Draft-only cold outreach: no network, scheduling or sending side effects."""
from datetime import timedelta
import unicodedata
from django.utils import timezone
from .rules import qualify


def weekdays_after(day, count):
    while count:
        day += timedelta(days=1)
        if day.weekday() < 5:
            count -= 1
    return day


def opening_for(segment):
    normalized = ''.join(c for c in unicodedata.normalize('NFD', segment.lower()) if not unicodedata.combining(c))
    if any(word in normalized for word in ('plaza', 'alianza')):
        return ('Asistencia para visitantes', 'Queremos explorar si les sería útil contar con un contacto de grúa para solicitudes de sus visitantes. En Taller Milenio revisamos cada caso según vehículo, ubicación y disponibilidad.\n\n¿Con qué área podríamos revisar esa posibilidad?')
    if any(word in normalized for word in ('mensaj', 'paquet')):
        return ('Vehículos de reparto', 'Si realizan reparto con autos, pickups o vans a gasolina, en Taller Milenio podemos revisar sus necesidades de mecánica en Tijuana.\n\n¿Operan vehículos propios de ese tipo o trabajan con transportistas externos?')
    if 'seguridad' in normalized or 'supervision' in normalized:
        return ('Vehículos de supervisión', 'Si su supervisión utiliza autos o pickups a gasolina, en Taller Milenio podemos revisar sus necesidades de mecánica en Tijuana.\n\n¿Quién coordina el mantenimiento de esas unidades?')
    if 'distribu' in normalized:
        return ('Vehículos de distribución', 'Si distribuyen con autos, pickups o vans a gasolina, en Taller Milenio podemos revisar sus necesidades de mecánica en Tijuana.\n\n¿Con quién podemos confirmar si operan vehículos propios de ese tipo?')
    return ('Vehículos de servicio', 'Si su equipo se desplaza en autos, pickups o vans a gasolina, en Taller Milenio podemos revisar sus necesidades de mecánica en Tijuana.\n\n¿Quién coordina el mantenimiento de esos vehículos?')


def prepare(account):
    result = dict(eligible=False, draft='', draft_label='Borrador de correo', suggested_on=None, block_reason='')
    if not qualify(account)['exploratory']:
        result['block_reason'] = 'Primero revisa identidad, fuente y contacto empresarial. Una baja impide preparar el contacto.'
    elif account.stage not in {'research', 'ready'}:
        result['block_reason'] = 'Esta etapa requiere seguimiento individual. Usa la conversación o propuesta existente.'
    elif account.interactions.filter(kind__in=['reply', 'meeting', 'bounce', 'optout']).exists():
        result['block_reason'] = 'Existe respuesta, reunión, rebote o baja. Revisa la bitácora y prepara una respuesta individual; la secuencia fría está detenida.'
    elif not account.contacts.filter(published_business=True).exclude(email='').exclude(deliverability='bounced').exists():
        result['block_reason'] = 'Falta un correo empresarial publicado o confirmado. Un teléfono por sí solo no habilita un borrador de correo.'
    if result['block_reason']:
        return result
    sent = list(account.interactions.filter(kind='sent').order_by('occurred_at', 'pk'))
    if len(sent) >= 3:
        result['block_reason'] = 'Ya hay tres contactos registrados. La secuencia exploratoria terminó; no generar más seguimientos en frío.'
        return result
    subject, body = opening_for(account.segment)
    label = 'Primer contacto'
    if len(sent) == 1:
        label = 'Primer seguimiento'
        if any(word in account.segment.lower() for word in ['plaza', 'alianza']):
            body = 'Para revisar una posible asistencia con grúa necesitaríamos conocer el vehículo y los puntos de origen y destino. La disponibilidad y cotización se confirman por solicitud.\n\n¿Les serviría revisar un procedimiento para canalizar solicitudes de sus visitantes?'
        else:
            body = 'Para evaluar una primera atención mecánica bastaría conocer tipo de unidad, combustible y motivo de servicio. Revisamos compatibilidad, disponibilidad y cotización antes de confirmar la atención.\n\n¿Les serviría revisar el caso de una unidad ligera a gasolina?'
        result['suggested_on'] = weekdays_after(timezone.localtime(sent[0].occurred_at).date(), 4)
    elif len(sent) == 2:
        label = 'Último seguimiento'
        body = 'Cierro por ahora esta consulta. Si más adelante necesitan revisar una atención con Taller Milenio, pueden localizarnos en el 664 820 1966.\n\nNo enviaré más seguimientos de esta consulta.'
        result['suggested_on'] = max(weekdays_after(timezone.localtime(sent[0].occurred_at).date(), 8), weekdays_after(timezone.localtime(sent[-1].occurred_at).date(), 4))
    result.update(eligible=True, draft_label=label, draft=f'Asunto: {subject}\n\nHola, equipo de {account.name}:\n\n{body}\n\nTaller Milenio · Tijuana\n664 820 1966\n\nSi prefieren no recibir seguimiento, indíquennoslo y lo registramos.')
    return result
