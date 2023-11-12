import { ComponentFixture, TestBed } from '@angular/core/testing';

import { RegistroAsistenciaComponent } from './registro-asistencia.component';

describe('RegistroAsistenciaComponent', () => {
  let component: RegistroAsistenciaComponent;
  let fixture: ComponentFixture<RegistroAsistenciaComponent>;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [RegistroAsistenciaComponent]
    });
    fixture = TestBed.createComponent(RegistroAsistenciaComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
