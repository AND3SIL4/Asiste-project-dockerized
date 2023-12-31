from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from apps.users.permission import IsAprendizUser, IsInstructorUser
from apps.asistencia.models import (
    Novedad,
    Aprendiz,
    Asistencia,
    Instructor,
    Ficha,
    HorarioPorDia,
)
from apps.asistencia.serializers import (
    NovedadSerializer,
    AprendizSerializer,
    AsistenciaSerializer,
    InstructorSerializer,
    FichaSerializer,
)
from rest_framework.views import Response, status
from django.db.models import Q
from rest_framework.decorators import action

from rest_framework.generics import UpdateAPIView


# ARCHIVO CON LA LOGICA DE NEGOCIOS PARA LA APP DE REGISTRO DE ASISTENCIA

class NovedadListView(ModelViewSet):
    queryset = Novedad.objects.all()
    serializer_class = NovedadSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]

    def get_queryset(self):
        user = self.request.user

        if IsAprendizUser().has_permission(self.request, self):
            # Aprendiz: puede ver sus propias novedades
            return self.queryset.filter(aprendiz__user=user)

        if IsInstructorUser().has_permission(self.request, self):
            # Instructor: puede ver novedades relacionadas con sus fichas
            fichas_del_instructor = Ficha.objects.filter(
                instructor__documento=user.document
            )
            return self.queryset.filter(
                aprendiz__ficha_aprendiz__in=fichas_del_instructor
            )

        # Si no es ninguno de los roles anteriores, no se permite el acceso
        return Novedad.objects.none()


# ACTUALIZAR DATOS DE APRENDIZ
class AprendizViewSet(ModelViewSet):
    serializer_class = AprendizSerializer
    permission_classes = [IsAuthenticated, IsAprendizUser]
    authentication_classes = [TokenAuthentication]

    def get_queryset(self):
        return Aprendiz.objects.filter(user=self.request.user)

    def perform_update(self, serializer):
        serializer.save()

    def patch(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


# CREAR NOVEDADES Y ESTADO DE ASISTENCIA DE APRENDICES
class AsistenciaViewSet(ReadOnlyModelViewSet):
    queryset = Asistencia.objects.all()
    serializer_class = AsistenciaSerializer
    permission_classes = [IsAuthenticated, IsAprendizUser]
    authentication_classes = [TokenAuthentication]

    def get_queryset(self):
        user = self.request.user

        try:
            # Intenta obtener el objeto Aprendiz a través de la clave foránea 'user'
            aprendiz = Aprendiz.objects.get(user=user)
            return self.queryset.filter(aprendiz=aprendiz)
        except Aprendiz.DoesNotExist:
            # Si el objeto Aprendiz no existe para el usuario, devuelve una consulta vacía
            return Asistencia.objects.none()


# NOVEDADES APRENDICES PARA INSTRUCTORES
class NovedadAprendizView(ReadOnlyModelViewSet):
    queryset = Novedad.objects.all()
    serializer_class = NovedadSerializer
    permission_classes = [IsAuthenticated, IsInstructorUser]
    authentication_classes = [TokenAuthentication]

    def get_queryset(self):
        user = self.request.user
        # Obtén al instructor relacionado con el usuario actual
        instructor = Instructor.objects.get(user=user)
        # Filtra las novedades por las fichas relacionadas con el instructor
        fichas_del_instructor = instructor.fichas.all()
        return Novedad.objects.filter(
            aprendiz__ficha_aprendiz__in=fichas_del_instructor
        )


# MODIFICAR NOVEDADES PARA SU ACEPTACIÓN
class NovedadAcceptanceView(ModelViewSet):
    queryset = Novedad.objects.all()
    serializer_class = NovedadSerializer
    permission_classes = [IsAuthenticated, IsInstructorUser]
    authentication_classes = [TokenAuthentication]

    def get_permissions(self):
        # Asignar el permiso adecuado según el tipo de usuario
        if self.request.user.is_authenticated:
            if self.request.user.user_type == "INSTRUCTOR":
                return [IsInstructorUser()]
            else:
                return []
        else:
            return []

    def update(self, request, *args, **kwargs):
        # Solo permitir actualización si el usuario es INSTRUCTOR
        if not (request.user.user_type == "INSTRUCTOR"):
            return Response(
                {"error": "No tienes permiso para realizar esta acción."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Procesar la actualización como de costumbre
        return super().update(request, *args, **kwargs)


# LISTA DE APRENDICES Y LLAMADO DE ASISTENCIA, POR INSTRUCTOR
class InstructorViewSet(ModelViewSet):
    serializer_class = InstructorSerializer
    permission_classes = [IsAuthenticated, IsInstructorUser]
    authentication_classes = [TokenAuthentication]

    @action(detail=True, methods=["GET"])
    def get_fichas(self, request, pk=None):
        instructor = self.get_object()
        fichas = instructor.fichas.all()
        fichas_serializer = FichaSerializer(fichas, many=True)
        return Response(fichas_serializer.data)

    @action(detail=True, methods=["PATCH"])
    def get_queryset(self):
        # Obtener el instructor asociado al usuario que ha iniciado sesión
        instructor = self.request.user.instructor

        # Devolver solo el instructor asociado al usuario actual
        return Instructor.objects.filter(documento=instructor.documento)

    @action(detail=True, methods=["PATCH"])
    def update_instructor(self, request, pk=None):
        # Obtener el instructor asociado al usuario que ha iniciado sesión
        instructor = self.request.user.instructor

        # Obtener el objeto del instructor asociado al usuario
        instance = Instructor.objects.get(documento=instructor.documento)

        # Obtener los datos enviados en el request
        data = request.data

        # Actualizar el objeto del instructor con los nuevos datos del request
        serializer = InstructorSerializer(instance, data=data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["GET"])
    def lista_aprendices(self, request, pk=None):
        instructor = self.get_object()
        ficha_id = request.query_params.get("ficha_id")

        # Verificar si el instructor está asociado a la ficha especificada
        if ficha_id not in [str(ficha.id_ficha) for ficha in instructor.fichas.all()]:
            return Response(
                {"error": "No tienes permiso para ver los aprendices de esta ficha."},
                status=status.HTTP_403_FORBIDDEN,
            )

        aprendices = Aprendiz.objects.filter(ficha_aprendiz__id_ficha=ficha_id)
        serializer = AprendizSerializer(aprendices, many=True)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @action(detail=True, methods=["POST"])
    def registrar_asistencia(self, request, pk=None):
        instructor = self.get_object()
        data = request.data

        # Asegurarse de que el usuario actual sea un Instructor y esté relacionado con este Instructor específico
        if not (
            request.user.user_type == "INSTRUCTOR" and instructor.user == request.user
        ):
            return Response(
                {
                    "error": "No tienes permiso para registrar asistencia para este instructor."
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        # Obtener la ficha y el horario asociado a la asistencia
        id_ficha = data.get("ficha_id")
        horario_id = data.get("horario_id")
        documento_aprendiz = data.get("documento_aprendiz")
        nombres_aprendiz = data.get("nombres_aprendiz")
        apellidos_aprendiz = data.get("apellidos_aprendiz")

        try:
            ficha = Ficha.objects.get(id_ficha=id_ficha)
        except Ficha.DoesNotExist:
            return Response(
                {"error": "Ficha no encontrada"}, status=status.HTTP_404_NOT_FOUND
            )

        try:
            horario = HorarioPorDia.objects.get(horario_id=horario_id)
        except HorarioPorDia.DoesNotExist:
            return Response(
                {"error": "Horario no existe"}, status=status.HTTP_404_NOT_FOUND
            )

        # Verificar si el aprendiz asociado a la asistencia pertenece a la ficha de este instructor
        try:
            aprendiz_data = data.get("aprendiz", {})
            if not isinstance(aprendiz_data, dict):
                return Response(
                    {
                        "error": "Datos del aprendiz no proporcionados o en un formato incorrecto."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            documento_aprendiz = aprendiz_data.get("documento_aprendiz")
            if documento_aprendiz is None:
                return Response(
                    {"error": "Documento del aprendiz no proporcionado."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            aprendiz = Aprendiz.objects.get(
                documento_aprendiz=documento_aprendiz, ficha_aprendiz=ficha
            )
        except Aprendiz.DoesNotExist:
            return Response(
                {"error": "Aprendiz no existe."}, status=status.HTTP_404_NOT_FOUND
            )

        # Crear la asistencia
        asistencia_data = {
            "aprendiz": aprendiz.pk,
            "fecha_asistencia": data.get("fecha_asistencia"),
            "presente": data.get("presente"),
        }

        asistencia_serializer = AsistenciaSerializer(data=asistencia_data)

        if asistencia_serializer.is_valid():
            asistencia_serializer.save()
            return Response(asistencia_serializer.data, status=status.HTTP_201_CREATED)

        return Response(
            asistencia_serializer.errors, status=status.HTTP_400_BAD_REQUEST
        )


# Metodo para obtener las asistencias de los aprendices
class VerAsistenciasInstructorViewSet(ModelViewSet):
    def list(self, request, instructor_id):
        aprendiz_documento = request.query_params.get("aprendiz_documento")

        try:
            instructor = Instructor.objects.get(documento=instructor_id)
            fichas = instructor.fichas.all()

            # Crear una lista para almacenar las asistencias
            asistencias = []

            for ficha in fichas:
                # Obtener las asistencias relacionadas con la ficha
                asistencias_ficha = Asistencia.objects.filter(
                    aprendiz__ficha_aprendiz=ficha
                )

                if aprendiz_documento:
                    # Filtrar por el documento del aprendiz si se proporciona
                    asistencias_ficha = asistencias_ficha.filter(
                        aprendiz__documento_aprendiz=aprendiz_documento
                    )

                asistencias.extend(asistencias_ficha)

            serializer = AsistenciaSerializer(asistencias, many=True)
            return Response(serializer.data)
        except Instructor.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)


class UpdateAsistenciaView(UpdateAPIView):
    queryset = Asistencia.objects.all()
    serializer_class = AsistenciaSerializer
    permission_classes = [IsAuthenticated, IsInstructorUser]

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
